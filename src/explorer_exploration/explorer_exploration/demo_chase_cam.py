"""
Demo chase camera: keeps the Gazebo GUI camera behind and above the robot as it drives, for the
review demo recording (user's request, 2026-10-24).

Drives Gazebo's own camera tracking (/gui/track, gz.msgs.CameraTrack, FOLLOW mode), so the
motion is rendered by the GUI at its frame rate. Gazebo applies follow_offset in the robot's frame
(checked 2026-10-24: an offset of x=-2 put the camera behind the robot's heading, not at world
-x), which would whip the camera round on every turn on the spot. So the camera follows a smoothed
heading instead: each tick the offset is rotated by (smoothed yaw - robot yaw), and the smoothed
yaw catches up with the robot's yaw with time constant yaw_tau seconds. follow_pgain smooths the
position on top of that.

Pure gz-transport, no ROS: it reads the robot pose from /world/<world>/dynamic_pose/info, so it
works the same under autonomous exploration and manual_drive. Run it in the sim's GZ_PARTITION.

    ros2 run explorer_exploration demo_chase_cam
    ros2 run explorer_exploration demo_chase_cam --distance 2.0 --height 1.2 --yaw-tau 2.0
"""

import argparse
import math
import re
import signal
import time

from gz.msgs10.cameratrack_pb2 import CameraTrack
from gz.msgs10.pose_v_pb2 import Pose_V
from gz.transport13 import Node


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def find_world(node, timeout_s):
    t_end = time.monotonic() + timeout_s
    while time.monotonic() < t_end:
        for t in node.topic_list():
            m = re.fullmatch(r'/world/([^/]+)/dynamic_pose/info', t)
            if m:
                return m.group(1)
        time.sleep(1.0)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--model', default='explorer', help='Gazebo model to follow')
    ap.add_argument('--world', default='', help='world name (default: first one found)')
    ap.add_argument('--distance', type=float, default=1.2, help='camera behind the robot (m)')
    ap.add_argument('--height', type=float, default=0.6, help='camera above the robot (m)')
    ap.add_argument('--look-height', type=float, default=0.1, help='point looked at, above the robot (m)')
    ap.add_argument('--yaw-tau', type=float, default=1.5,
                    help='heading smoothing time constant (s); 0 = strictly behind')
    ap.add_argument('--pgain', type=float, default=0.05, help='Gazebo follow P gain, 0..1 (lower = smoother)')
    ap.add_argument('--rate', type=float, default=30.0, help='update rate (Hz)')
    ap.add_argument('--wait', type=float, default=120.0, help='wait this long for Gazebo (s)')
    args, _ = ap.parse_known_args()        # ignore --ros-args from ros2 launch

    node = Node()
    world = args.world or find_world(node, args.wait)
    if not world:
        print(f'demo_chase_cam: no Gazebo world found in {args.wait:.0f} s (GZ_PARTITION?)', flush=True)
        return
    state = {}

    def on_poses(msg):
        for p in msg.pose:
            if p.name == args.model:
                q = p.orientation
                state['yaw'] = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
                return

    node.subscribe(Pose_V, f'/world/{world}/dynamic_pose/info', on_poses)
    pub = node.advertise('/gui/track', CameraTrack)
    print(f'demo_chase_cam: following {args.model} in world {world} '
          f'({args.distance} m behind, {args.height} m up, yaw_tau {args.yaw_tau} s)', flush=True)

    running = [True]
    signal.signal(signal.SIGINT, lambda *_: running.__setitem__(0, False))
    signal.signal(signal.SIGTERM, lambda *_: running.__setitem__(0, False))

    msg = CameraTrack()
    msg.track_mode = CameraTrack.FOLLOW
    msg.follow_target.name = args.model
    msg.track_target.name = args.model
    msg.track_offset.z = args.look_height
    msg.follow_pgain = args.pgain
    period = 1.0 / args.rate
    smooth_yaw, last = None, time.monotonic()
    while running[0]:
        time.sleep(period)
        now = time.monotonic()
        dt, last = now - last, now
        yaw = state.get('yaw')
        if yaw is None:
            continue
        if smooth_yaw is None or args.yaw_tau <= 0:
            smooth_yaw = yaw
        else:
            smooth_yaw = wrap(smooth_yaw + wrap(yaw - smooth_yaw) * (1.0 - math.exp(-dt / args.yaw_tau)))
        rel = smooth_yaw - yaw                 # offset is applied in the robot's frame
        msg.follow_offset.x = -args.distance * math.cos(rel)
        msg.follow_offset.y = -args.distance * math.sin(rel)
        msg.follow_offset.z = args.height
        pub.publish(msg)


if __name__ == '__main__':
    main()
