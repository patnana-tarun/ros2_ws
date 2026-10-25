"""
Demo HUD: live exploration progress in the RViz demo view (user's request, 2026-10-25): explored
share of the cave and elapsed time, drawn as text on a dark plate in the view box's frame
(view_anchor), so it moves with the view and is in the recording.

    Explored 63.4%  /  Time 07:42      (two lines)
    95% at 08:41                         (once target_pct is passed)
    Done in 10:12                        (on /exploration_complete)

Explored % is the measure the experiments report (sim_loop.py / rosview.py coverage()): known map
cells over the cave's true floor, from field_file, which is made for cave.sdf. The map frame
starts at the spawn pose, so map cells are moved by spawn_x, spawn_y, spawn_yaw into the world
frame first. Without the field file (another world) it shows the mapped area in m2 instead.
Time is sim time from the robot's first move (it waits ~8 s for Nav2 at start).

The plate is an interactive marker (server namespace /demo_hud): pick RViz's Interact tool
(toolbar, or key i) and drag it anywhere; it keeps that place relative to the view. Where it was
dropped is saved to position_file and used at the next start. hud_x / hud_y (m from the view
centre, x right, y up) override it; neither = just above the view box.

    ros2 run explorer_exploration demo_hud --ros-args -p use_sim_time:=true
    ros2 run explorer_exploration demo_hud --ros-args -p use_sim_time:=true -p spawn_x:=9.0 -p spawn_y:=-1.5
    ros2 run explorer_exploration demo_hud --ros-args -p use_sim_time:=true -p hud_x:=-3.0 -p hud_y:=5.0
"""

import json
import math
import os

import numpy as np
import rclpy
from interactive_markers import InteractiveMarkerServer
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Empty
from visualization_msgs.msg import (InteractiveMarker, InteractiveMarkerControl,
                                    InteractiveMarkerFeedback, Marker)


def mmss(s):
    s = max(0, int(s))
    return f'{s // 60:02d}:{s % 60:02d}'


class DemoHud(Node):
    def __init__(self):
        super().__init__('demo_hud')
        self.declare_parameter('field_file',
                               os.path.expanduser('~/ros2_ws/data/demo_runs_2026-10-19/field.npz'))
        self.declare_parameter('spawn_x', 0.0)
        self.declare_parameter('spawn_y', 0.0)
        self.declare_parameter('spawn_yaw', 0.0)
        self.declare_parameter('target_pct', 95.0)
        self.declare_parameter('anchor_frame', 'view_anchor')
        self.declare_parameter('box_y', 4.0)            # view box height: text goes above it
        self.declare_parameter('text_height', 0.35)     # m (80 px/m in demo_view.rviz)
        self.declare_parameter('hud_x', float('nan'))   # plate centre from the view centre (m)
        self.declare_parameter('hud_y', float('nan'))
        self.declare_parameter('position_file', os.path.expanduser('~/.ros/demo_hud_position.json'))
        g = lambda n: self.get_parameter(n).value
        self.sx, self.sy, self.syaw = g('spawn_x'), g('spawn_y'), g('spawn_yaw')
        self.target, self.anchor = g('target_pct'), g('anchor_frame')
        self.h, self.pos_file = g('text_height'), g('position_file')
        self.pos = self.initial_position(g('hud_x'), g('hud_y'), g('box_y'))

        self.floor = None
        path = g('field_file')
        if path and os.path.exists(path):
            f = np.load(path)
            self.floor = f['s'] < 0
            self.f_res, self.f_x0, self.f_y0 = float(f['res']), float(f['XMIN']), float(f['YMIN'])
            self.floor_m2 = float(self.floor.sum()) * self.f_res ** 2
        else:
            self.get_logger().warn(f'no field file {path!r}: showing mapped area, not explored %')

        self.pct = self.area = None
        self.t_start = self.t_target = self.t_done = None
        map_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(OccupancyGrid, '/map', self.map_cb, map_qos)
        self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.create_subscription(Empty, '/exploration_complete', self.complete_cb, 10)
        self.server = InteractiveMarkerServer(self, 'demo_hud')
        self.dragging, self.shown = False, None
        self.create_timer(0.5, self.tick)

    def initial_position(self, hx, hy, box_y):
        if math.isfinite(hx) and math.isfinite(hy):
            return hx, hy
        try:
            with open(self.pos_file) as f:
                p = json.load(f)
            return float(p['x']), float(p['y'])
        except (OSError, ValueError, KeyError):
            return 0.0, box_y / 2.0 + 0.5 + 1.4 * self.h      # just above the view box

    def on_feedback(self, fb):
        if fb.event_type == InteractiveMarkerFeedback.MOUSE_DOWN:
            self.dragging = True
        elif fb.event_type == InteractiveMarkerFeedback.POSE_UPDATE:
            self.pos = (fb.pose.position.x, fb.pose.position.y)
        elif fb.event_type == InteractiveMarkerFeedback.MOUSE_UP:
            self.dragging = False
            self.pos = (fb.pose.position.x, fb.pose.position.y)
            try:
                os.makedirs(os.path.dirname(self.pos_file), exist_ok=True)
                with open(self.pos_file, 'w') as f:
                    json.dump({'x': round(self.pos[0], 2), 'y': round(self.pos[1], 2)}, f)
            except OSError as e:
                self.get_logger().warn(f'could not save the HUD position: {e}')
            self.get_logger().info(f'HUD moved to x={self.pos[0]:.2f} y={self.pos[1]:.2f} '
                                   f'(saved to {self.pos_file})')

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def elapsed(self):
        return 0.0 if self.t_start is None else self.now_s() - self.t_start

    def odom_cb(self, msg):
        # sim time reads 0 until the first /clock: a start taken then would count from the sim's start
        if self.t_start is None and self.now_s() > 0 and \
                (abs(msg.twist.twist.linear.x) > 0.02 or abs(msg.twist.twist.angular.z) > 0.05):
            self.t_start = self.now_s()

    def complete_cb(self, _msg):
        if self.t_done is None:
            self.t_done = self.elapsed()

    def map_cb(self, m):
        a = np.asarray(m.data, dtype=np.int16).reshape(m.info.height, m.info.width)
        res = m.info.resolution
        known = a >= 0
        self.area = float(known.sum()) * res ** 2
        if self.floor is None:
            return
        iy, ix = np.nonzero(known)
        mx = m.info.origin.position.x + (ix + 0.5) * res
        my = m.info.origin.position.y + (iy + 0.5) * res
        c, s = math.cos(self.syaw), math.sin(self.syaw)
        wx, wy = self.sx + c * mx - s * my, self.sy + s * mx + c * my
        gi = np.floor((wy - self.f_y0) / self.f_res + 0.5).astype(int)
        gj = np.floor((wx - self.f_x0) / self.f_res + 0.5).astype(int)
        ok = (gi >= 0) & (gi < self.floor.shape[0]) & (gj >= 0) & (gj < self.floor.shape[1])
        seen = np.zeros(self.floor.shape, bool)
        seen[gi[ok], gj[ok]] = True
        self.pct = 100.0 * float((seen & self.floor).sum()) * self.f_res ** 2 / self.floor_m2
        if self.t_target is None and self.pct >= self.target:
            self.t_target = self.elapsed()
            self.get_logger().info(f'{self.target:.0f} % reached at {mmss(self.t_target)}')

    def text(self):
        # short lines, few spaces: RViz draws a space about 4x as wide as a letter
        if self.pct is not None:
            progress = f'Explored {self.pct:.1f}%'
        elif self.area is not None:
            progress = f'Mapped {self.area:.1f}m2'
        else:
            progress = 'Waiting for map'
        clock = 'Time 00:00' if self.t_start is None else \
            f'Time {mmss(self.t_done if self.t_done is not None else self.elapsed())}'
        lines = [progress, clock]
        if self.t_target is not None:
            lines.append(f'{self.target:.0f}% at {mmss(self.t_target)}')
        if self.t_done is not None:
            lines.append(f'Done in {mmss(self.t_done)}')
        return lines

    def tick(self):
        lines = self.text()
        # re-inserting the marker resets it to self.pos: not while it is being dragged
        if self.dragging or lines == self.shown:
            return
        self.shown = lines
        h = self.h
        # glyph widths measured in RViz (2026-10-25): ~0.45 h per character, ~1.75 h per space
        width = max(len(s) * 0.45 + s.count(' ') * 1.3 for s in lines) * h + 1.0 * h
        height = len(lines) * 1.25 * h + 0.5 * h

        plate = Marker(type=Marker.CUBE)
        plate.pose.position.z = 0.2
        plate.pose.orientation.w = 1.0
        plate.scale.x, plate.scale.y, plate.scale.z = width, height, 0.01
        plate.color.r = plate.color.g = plate.color.b = 0.08
        plate.color.a = 0.85

        txt = Marker(type=Marker.TEXT_VIEW_FACING)
        txt.pose.position.z = 0.5
        txt.pose.orientation.w = 1.0
        txt.scale.z = h
        txt.color.r, txt.color.g, txt.color.b, txt.color.a = 1.0, 1.0, 1.0, 1.0
        if self.t_done is not None or self.t_target is not None:
            txt.color.b = 0.4                   # turns yellow once the target is reached
        txt.text = '\n'.join(lines)

        # drag in the map plane: MOVE_PLANE moves normal to the control's x axis, turned onto z
        ctrl = InteractiveMarkerControl(name='move', always_visible=True,
                                        interaction_mode=InteractiveMarkerControl.MOVE_PLANE)
        ctrl.orientation.w = ctrl.orientation.y = math.sqrt(0.5)
        ctrl.markers = [plate, txt]

        im = InteractiveMarker(name='hud', description='', scale=max(width, height))
        im.header.frame_id = self.anchor
        im.header.stamp = self.get_clock().now().to_msg()
        im.pose.position.x, im.pose.position.y = self.pos
        im.pose.orientation.w = 1.0
        im.controls = [ctrl]
        self.server.insert(im, feedback_callback=self.on_feedback)
        self.server.applyChanges()


def main():
    rclpy.init()
    node = DemoHud()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
