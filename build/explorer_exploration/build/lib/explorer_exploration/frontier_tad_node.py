"""
Frontier detector + TAD scorer, combined into one node for the first
implementation pass. Reads the live occupancy grid, finds frontier cell
clusters, scores each with a grid-adapted TAD score (distance, adjacent,
trapezoid), and publishes the best one as a goal pose. Also publishes a
MarkerArray so every candidate is visible in RViz2, colored by whether
it was the winner.

Grid adaptation of Buriboev, Choi & Jeon (2025) "Optimized Frontier-Based
Path Planning Using the TAD Algorithm", Electronics 14(1), 74:
  - d_n: exact Euclidean distance, robot pose -> frontier centroid (Eq. 2).
  - a_n: size of the connected unknown-cell region touching the frontier
    cluster - the paper defines a_n as "the corresponding frontier
    encompasses a larger unexplored area", which is a region-size measure
    on our raw occupancy grid rather than the paper's rectangle-overlap
    measure (their a_n is defined over Rmap rectangles, which we don't
    build here).
  - t_n: the paper's literal rule (Eq. 5) - compare the frontier's outer
    size (within long sensor range) against its inner size (within short
    sensor range); t_n = 1 if outer > inner, 0 if equal, -1 if outer <
    inner. We measure "size" as cell count within each annulus since we
    don't have the paper's inner/outer arc lengths on a raw grid.

This node re-runs on every /map update and simply republishes /best_goal.
The explore_coordinator node decides when to actually act on it (see that
file for why this keeps the two nodes decoupled).
"""

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rclpy.time import Time
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PoseStamped
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import Empty
from scipy import ndimage
import tf2_ros
from tf2_ros import TransformException


class FrontierTADNode(Node):
    def __init__(self):
        super().__init__('frontier_tad_node')

        # Tunable weights - start here, adjust once you see behavior in RViz2.
        # These are NOT 1:1:1 like the original TAD paper because d/a/t are
        # grid-adapted proxies on different scales - see the README.
        self.declare_parameter('w_distance', 1.0)
        self.declare_parameter('w_adjacency', 1.0)
        self.declare_parameter('w_trapezoid', 1.0)
        # 7 cells @ 0.05 m/cell resolution ~= 0.35 m, matching the paper's
        # Table 2 "Minimal size of frontier: 0.35 m" constant (was an
        # undocumented placeholder of 5 before this V0->V1 experiment).
        self.declare_parameter('min_frontier_size', 7)
        # Short/long sensor range (metres) for the paper's inner/outer
        # trapezoid comparison (Eq. 5) - defaults match the explorer's
        # YDLIDAR X2 (0.12-8 m; 6 m is its reliable range on dark rock).
        self.declare_parameter('sensor_short_range', 0.5)
        self.declare_parameter('sensor_long_range', 6.0)
        # Close unknown gaps up to ~2*N cells wide inside mapped space before
        # detecting frontiers. At range, adjacent LiDAR rays land several cells
        # apart (YDLIDAR X2: 0.84 deg -> 7 cm at 5 m), so SLAM leaves unknown
        # speckles between rays. Without this, every speckle is a frontier, they
        # merge into one cluster whose centroid is the robot itself, and the
        # robot never moves. 0 = original behaviour (no gap filling).
        self.declare_parameter('unknown_gap_fill', 2)
        # Robot frame for the pose lookup. The explorer's odometry and Nav2
        # use base_footprint (TurtleBot3 used base_link).
        self.declare_parameter('robot_frame', 'base_footprint')
        # 'tad' = paper's d+a+t scoring (Eq. 6). 'nearest' = classic
        # Yamauchi nearest-frontier baseline (score = -d_n only, a/t
        # ignored) - for A/B comparison against the paper's own baseline.
        self.declare_parameter('scoring_mode', 'tad')

        self.w_d = self.get_parameter('w_distance').value
        self.w_a = self.get_parameter('w_adjacency').value
        self.w_t = self.get_parameter('w_trapezoid').value
        self.min_frontier_size = self.get_parameter('min_frontier_size').value
        self.short_range = self.get_parameter('sensor_short_range').value
        self.long_range = self.get_parameter('sensor_long_range').value
        self.scoring_mode = self.get_parameter('scoring_mode').value
        self.robot_frame = self.get_parameter('robot_frame').value
        self.gap_fill = self.get_parameter('unknown_gap_fill').value

        # map topic from slam_toolbox is latched - match its QoS or you'll miss it
        map_qos = QoSProfile(depth=1)
        map_qos.reliability = ReliabilityPolicy.RELIABLE
        map_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL

        self.map_sub = self.create_subscription(
            OccupancyGrid, '/map', self.map_callback, map_qos)

        self.goal_pub = self.create_publisher(PoseStamped, '/best_goal', 10)
        self.marker_pub = self.create_publisher(MarkerArray, '/frontier_markers', 10)
        self.complete_pub = self.create_publisher(Empty, '/exploration_complete', 10)

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.get_logger().info('Frontier + TAD scorer node started')

    def map_callback(self, msg: OccupancyGrid):
        self.process_map(msg)

    def get_robot_pose(self):
        try:
            t = self.tf_buffer.lookup_transform('map', self.robot_frame, Time())
            return t.transform.translation.x, t.transform.translation.y
        except TransformException as ex:
            self.get_logger().warn(f'Could not get robot pose yet: {ex}')
            return None

    def process_map(self, msg: OccupancyGrid):
        width = msg.info.width
        height = msg.info.height
        resolution = msg.info.resolution
        origin_x = msg.info.origin.position.x
        origin_y = msg.info.origin.position.y

        grid = np.array(msg.data, dtype=np.int16).reshape((height, width))

        free = (grid == 0)
        unknown = (grid == -1)
        obstacle = (grid >= 50)

        # Unknown cells enclosed by mapped cells (gaps between LiDAR rays) are
        # not unexplored space - see unknown_gap_fill. Morphological closing of
        # the mapped (free or obstacle) mask finds them; they are counted as
        # free, so a tunnel mouth seen through sparse rays becomes one solid
        # frontier instead of scattered single cells. Both the frontier test and
        # a_n below then only see real unknown regions.
        if self.gap_fill > 0:
            mapped = ndimage.binary_closing(
                free | obstacle, structure=np.ones((3, 3), dtype=bool),
                iterations=self.gap_fill)
            free = free | (unknown & mapped)
            unknown = unknown & ~mapped

        # A frontier cell is a free cell with at least one unknown neighbor
        # (4-connectivity). Shifted boolean comparisons instead of a Python
        # loop, since this runs on every map update.
        frontier_mask = np.zeros_like(free, dtype=bool)
        frontier_mask[:-1, :] |= free[:-1, :] & unknown[1:, :]
        frontier_mask[1:, :] |= free[1:, :] & unknown[:-1, :]
        frontier_mask[:, :-1] |= free[:, :-1] & unknown[:, 1:]
        frontier_mask[:, 1:] |= free[:, 1:] & unknown[:, :-1]

        if not np.any(frontier_mask):
            self.get_logger().info('No frontiers left - exploration complete')
            self.clear_markers()
            self.complete_pub.publish(Empty())
            return

        # 8-connectivity when grouping frontier cells into clusters. A frontier
        # is a curve through the grid and mostly runs diagonally; under
        # 4-connectivity a diagonal run is a staircase whose cells touch only
        # at their corners, so a single real frontier is split into many tiny
        # fragments and min_frontier_size then discards all of them. Measured
        # on a representative partially-explored map: 4-connectivity gave 76
        # clusters (largest 8 cells) where 8-connectivity gives 24 (largest
        # 75), and exploration stalled below 10% coverage instead of reaching
        # 98%. Frontier cell DETECTION above stays 4-neighbour, which is the
        # standard definition.
        labeled, num_clusters = ndimage.label(
            frontier_mask, structure=np.ones((3, 3), dtype=bool))

        # a_n: label the connected unknown-cell regions once; each frontier
        # cluster looks up the size of whichever unknown region it borders.
        unknown_labeled, _ = ndimage.label(unknown)
        unknown_region_sizes = np.bincount(unknown_labeled.ravel())

        robot_pose = self.get_robot_pose()
        if robot_pose is None:
            return
        rx, ry = robot_pose
        rcol = (rx - origin_x) / resolution
        rrow = (ry - origin_y) / resolution

        candidates = []
        for cluster_id in range(1, num_clusters + 1):
            ys, xs = np.where(labeled == cluster_id)
            cell_count = len(xs)
            if cell_count < self.min_frontier_size:
                continue

            centroid_row = float(np.mean(ys))
            centroid_col = float(np.mean(xs))

            wx = origin_x + centroid_col * resolution
            wy = origin_y + centroid_row * resolution

            d_n = float(np.hypot(wx - rx, wy - ry))

            # a_n: size of the unexplored region this frontier borders.
            unknown_row_off = ys + np.array([-1, 1, 0, 0])[:, None]
            unknown_col_off = xs + np.array([0, 0, -1, 1])[:, None]
            touched_labels = set()
            for r_off, c_off in zip(unknown_row_off, unknown_col_off):
                valid = (r_off >= 0) & (r_off < height) & (c_off >= 0) & (c_off < width)
                for r, c in zip(r_off[valid], c_off[valid]):
                    lbl = unknown_labeled[r, c]
                    if lbl != 0:
                        touched_labels.add(lbl)
            a_n = float(sum(unknown_region_sizes[l] for l in touched_labels)) * (resolution ** 2)

            # t_n: paper's literal inner/outer rule (Eq. 5). "Size" here is
            # the frontier cell count within each annulus around the robot.
            cell_dist = np.hypot(xs - rcol, ys - rrow) * resolution
            inner_size = int(np.sum(cell_dist <= self.short_range))
            outer_size = int(np.sum((cell_dist > self.short_range) & (cell_dist <= self.long_range)))
            if outer_size > inner_size:
                t_n = 1.0
            elif outer_size == inner_size:
                t_n = 0.0
            else:
                t_n = -1.0

            candidates.append({
                'x': wx, 'y': wy, 'd': d_n, 'a': a_n, 't': t_n,
                'cell_count': cell_count,
            })

        if not candidates:
            self.get_logger().info(
                'No frontier clusters above min size - exploration complete')
            self.clear_markers()
            self.complete_pub.publish(Empty())
            return

        def normalize(values):
            values = np.array(values, dtype=float)
            v_min, v_max = values.min(), values.max()
            if v_max - v_min < 1e-6:
                return np.ones_like(values)
            return (values - v_min) / (v_max - v_min)

        if self.scoring_mode == 'nearest':
            # Classic Yamauchi baseline: always the closest frontier.
            scores = -np.array([c['d'] for c in candidates])
        else:
            d_vals = normalize([c['d'] for c in candidates])
            a_vals = normalize([c['a'] for c in candidates])
            t_vals = normalize([c['t'] for c in candidates])
            scores = self.w_d * d_vals + self.w_a * a_vals + self.w_t * t_vals
        best_idx = int(np.argmax(scores))
        best = candidates[best_idx]

        self.publish_markers(candidates, scores, best_idx)
        self.publish_goal(best)

        self.get_logger().info(
            f'Chose frontier at ({best["x"]:.2f}, {best["y"]:.2f}) '
            f'score={scores[best_idx]:.2f} among {len(candidates)} candidates')

    def publish_goal(self, best):
        goal = PoseStamped()
        goal.header.frame_id = 'map'
        goal.header.stamp = self.get_clock().now().to_msg()
        goal.pose.position.x = best['x']
        goal.pose.position.y = best['y']
        goal.pose.orientation.w = 1.0
        self.goal_pub.publish(goal)

    def clear_markers(self):
        marker_array = MarkerArray()
        delete_all = Marker()
        delete_all.action = Marker.DELETEALL
        marker_array.markers.append(delete_all)
        self.marker_pub.publish(marker_array)

    def publish_markers(self, candidates, scores, best_idx):
        marker_array = MarkerArray()
        delete_all = Marker()
        delete_all.action = Marker.DELETEALL
        marker_array.markers.append(delete_all)
        for i, (c, s) in enumerate(zip(candidates, scores)):
            marker = Marker()
            marker.header.frame_id = 'map'
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = 'frontiers'
            marker.id = i
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose.position.x = c['x']
            marker.pose.position.y = c['y']
            marker.pose.orientation.w = 1.0
            marker.scale.x = marker.scale.y = marker.scale.z = 0.15
            if i == best_idx:
                # Winner: green
                marker.color.r, marker.color.g, marker.color.b, marker.color.a = (
                    0.0, 1.0, 0.0, 1.0)
            else:
                # Candidates: orange, translucent
                marker.color.r, marker.color.g, marker.color.b, marker.color.a = (
                    1.0, 0.5, 0.0, 0.6)
            marker_array.markers.append(marker)
        self.marker_pub.publish(marker_array)


def main(args=None):
    rclpy.init(args=args)
    node = FrontierTADNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
