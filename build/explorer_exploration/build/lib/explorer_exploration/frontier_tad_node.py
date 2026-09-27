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
from scipy import sparse
from scipy.sparse.csgraph import dijkstra
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rclpy.time import Time
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PointStamped, PoseStamped
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
        # How the scored candidates become a goal.
        # 'dfs' (default): depth-first. Only frontiers whose travel distance
        #   (along free space, not straight line) is within dfs_ratio x (or
        #   dfs_margin m more than) the nearest frontier's are eligible; the best
        #   TAD score among them wins. The robot finishes the branch it is in
        #   before crossing the map, and at a dead end the nearest remaining
        #   frontier - the branch it most recently passed - comes next, like
        #   DFS backtracking. Frontiers it cannot reach are dropped.
        # 'global': the original behaviour - best TAD score anywhere.
        self.declare_parameter('selection_mode', 'dfs')
        self.declare_parameter('dfs_ratio', 1.5)
        self.declare_parameter('dfs_margin', 2.0)
        # 'dfs' only: skip frontiers whose unknown region (a_n) is smaller than this.
        # Every rock casts a LiDAR shadow - a small unknown pocket enclosed by free
        # space and the rock - and each pocket is a frontier. Preferring near
        # frontiers, 'dfs' otherwise tours every rock in a chamber. A real opening
        # borders the large unexplored rest of the cave instead.
        self.declare_parameter('min_pocket_area', 1.0)
        # Frontiers near a goal Nav2 failed to reach are skipped for a while
        # (explore_coordinator reports failures on /frontier_blacklist).
        self.declare_parameter('blacklist_radius', 0.5)
        self.declare_parameter('blacklist_duration', 300.0)

        self.w_d = self.get_parameter('w_distance').value
        self.w_a = self.get_parameter('w_adjacency').value
        self.w_t = self.get_parameter('w_trapezoid').value
        self.min_frontier_size = self.get_parameter('min_frontier_size').value
        self.short_range = self.get_parameter('sensor_short_range').value
        self.long_range = self.get_parameter('sensor_long_range').value
        self.scoring_mode = self.get_parameter('scoring_mode').value
        self.robot_frame = self.get_parameter('robot_frame').value
        self.gap_fill = self.get_parameter('unknown_gap_fill').value
        self.selection_mode = self.get_parameter('selection_mode').value
        self.dfs_ratio = self.get_parameter('dfs_ratio').value
        self.dfs_margin = self.get_parameter('dfs_margin').value
        self.min_pocket = self.get_parameter('min_pocket_area').value
        self.bl_radius = self.get_parameter('blacklist_radius').value
        self.bl_duration = self.get_parameter('blacklist_duration').value
        self.blacklist = []     # (x, y, time added)
        self.create_subscription(PointStamped, '/frontier_blacklist', self.blacklist_cb, 10)

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

    def blacklist_cb(self, msg: PointStamped):
        self.blacklist.append((msg.point.x, msg.point.y, self.get_clock().now()))
        self.get_logger().info(
            f'Blacklisted frontiers near ({msg.point.x:.2f}, {msg.point.y:.2f}) '
            f'for {self.bl_duration:.0f} s')

    def blacklisted(self, x, y):
        now = self.get_clock().now()
        self.blacklist = [b for b in self.blacklist
                          if (now - b[2]).nanoseconds / 1e9 < self.bl_duration]
        return any(np.hypot(x - bx, y - by) < self.bl_radius for bx, by, _ in self.blacklist)

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

        # Travel distance from the robot to every free cell (for 'dfs').
        travel = None
        if self.selection_mode == 'dfs':
            travel = self.travel_distances(free, obstacle, rrow, rcol, resolution)

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

            # Travel distance to the nearest cell of the cluster (inf = unreachable).
            travel_n = float(travel[ys, xs].min()) if travel is not None else d_n

            # Goal point: the centroid can fall inside a wall or among rocks, so in 'dfs'
            # mode use the reachable cluster cell nearest to the centroid instead.
            gx, gy = wx, wy
            if travel is not None and np.isfinite(travel_n):
                ok = np.isfinite(travel[ys, xs])
                k = np.argmin(np.hypot(xs[ok] - centroid_col, ys[ok] - centroid_row))
                gx = origin_x + xs[ok][k] * resolution
                gy = origin_y + ys[ok][k] * resolution
            if self.blacklisted(gx, gy) or self.blacklisted(wx, wy):
                continue
            if self.selection_mode == 'dfs' and a_n < self.min_pocket:
                continue    # LiDAR shadow behind a rock, not an opening

            candidates.append({
                'x': gx, 'y': gy, 'd': d_n, 'a': a_n, 't': t_n,
                'cell_count': cell_count, 'travel': travel_n,
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

        # Which candidates may be chosen. TAD scores above are unchanged; 'dfs'
        # only restricts the choice to frontiers along the current branch.
        eligible = np.ones(len(candidates), dtype=bool)
        if self.selection_mode == 'dfs':
            travel = np.array([c['travel'] for c in candidates])
            reachable = np.isfinite(travel)
            if reachable.any():
                nearest = travel[reachable].min()
                window = max(self.dfs_ratio * nearest, nearest + self.dfs_margin)
                eligible = reachable & (travel <= window)
            # else: the robot's own cell is not in the free map yet (startup) -
            # fall back to every candidate rather than stalling.
        best_idx = int(np.argmax(np.where(eligible, scores, -np.inf)))
        best = candidates[best_idx]

        self.publish_markers(candidates, scores, best_idx, eligible)
        self.publish_goal(best)

        self.get_logger().info(
            f'Chose frontier at ({best["x"]:.2f}, {best["y"]:.2f}) '
            f'score={scores[best_idx]:.2f} travel={best["travel"]:.1f} m, '
            f'{int(eligible.sum())} of {len(candidates)} candidates eligible')

    def travel_distances(self, free, obstacle, rrow, rcol, resolution):
        """Shortest 8-connected path length (m) through free cells from the
        robot to every cell; inf where unreachable. Cells next to an obstacle
        are excluded so paths don't squeeze through gaps the robot can't."""
        h, w = free.shape
        passable = free & ~ndimage.binary_dilation(obstacle, iterations=1)
        r0, c0 = int(round(rrow)), int(round(rcol))
        # The robot's own cell may not be free yet (start-up, or inflated);
        # start from the nearest passable cell within 0.5 m.
        rad = int(0.5 / resolution)
        rs, cs = np.nonzero(passable[max(r0 - rad, 0):r0 + rad + 1, max(c0 - rad, 0):c0 + rad + 1])
        if len(rs) == 0:
            return np.full((h, w), np.inf)
        k = np.argmin(np.hypot(rs + max(r0 - rad, 0) - r0, cs + max(c0 - rad, 0) - c0))
        start = (rs[k] + max(r0 - rad, 0)) * w + cs[k] + max(c0 - rad, 0)

        idx = np.arange(h * w).reshape(h, w)
        rows, cols, wts = [], [], []
        # Edges to the right, down, down-right and down-left neighbours
        for dr, dc, cost in ((0, 1, 1.0), (1, 0, 1.0), (1, 1, 1.4142), (1, -1, 1.4142)):
            c0, c1 = max(0, -dc), w - max(0, dc)
            a = passable[0:h - dr, c0:c1]
            b = passable[dr:h, c0 + dc:c1 + dc]
            m = a & b
            rows.append(idx[0:h - dr, c0:c1][m])
            cols.append(idx[dr:h, c0 + dc:c1 + dc][m])
            wts.append(np.full(m.sum(), cost))
        graph = sparse.csr_matrix(
            (np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))), shape=(h * w, h * w))
        dist = dijkstra(graph, directed=False, indices=start)
        # Frontier cells themselves may touch an obstacle: give them the distance
        # of their best passable neighbour plus one step.
        dist = dist.reshape(h, w) * resolution
        near = ndimage.grey_erosion(np.where(np.isfinite(dist), dist, 1e9), size=(3, 3)) + resolution
        dist = np.where(np.isfinite(dist), dist, np.where(near < 1e8, near, np.inf))
        return dist

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

    def publish_markers(self, candidates, scores, best_idx, eligible=None):
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
            elif eligible is None or eligible[i]:
                # Candidates: orange, translucent
                marker.color.r, marker.color.g, marker.color.b, marker.color.a = (
                    1.0, 0.5, 0.0, 0.6)
            else:
                # Outside the depth-first window (selection_mode 'dfs'): grey
                marker.color.r, marker.color.g, marker.color.b, marker.color.a = (
                    0.6, 0.6, 0.6, 0.5)
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
