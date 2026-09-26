"""
Test harness that drives the PRODUCTION FrontierTADNode directly.

Nothing here re-implements TAD. It constructs the real node, injects a
synthetic OccupancyGrid, and intercepts the node's own publish_markers()
call to recover the per-candidate d_n / a_n / t_n / F_n it computed. Any
result produced through this harness is therefore evidence about
explorer_exploration/frontier_tad_node.py itself.
"""

import os
import sys

import numpy as np
import rclpy
from nav_msgs.msg import OccupancyGrid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from explorer_exploration.frontier_tad_node import FrontierTADNode  # noqa: E402

_NODE = None


def get_node():
    """One long-lived real node, reused across every test."""
    global _NODE
    if _NODE is None:
        if not rclpy.ok():
            rclpy.init()
        _NODE = FrontierTADNode()
    return _NODE


def make_grid(array, resolution=1.0, origin=(0.0, 0.0)):
    """Wrap a numpy array as a real nav_msgs/OccupancyGrid."""
    array = np.asarray(array, dtype=np.int16)
    msg = OccupancyGrid()
    msg.info.width = int(array.shape[1])
    msg.info.height = int(array.shape[0])
    msg.info.resolution = float(resolution)
    msg.info.origin.position.x = float(origin[0])
    msg.info.origin.position.y = float(origin[1])
    msg.data = [int(v) for v in array.ravel()]
    return msg


def score(array, robot_xy, resolution=1.0, origin=(0.0, 0.0),
          min_frontier_size=1, short_range=0.5, long_range=3.5,
          w_d=1.0, w_a=1.0, w_t=1.0, scoring_mode='tad'):
    """Run the production scoring path; return its internal candidates.

    Returns (candidates, scores, best_idx) exactly as the node computed
    them, or (None, None, None) if the node bailed out (no frontiers).
    """
    node = get_node()

    # Drive the real compute path with these settings. process_map() reads
    # these attributes at call time, so the production code is unmodified.
    node.min_frontier_size = min_frontier_size
    node.short_range = short_range
    node.long_range = long_range
    node.w_d, node.w_a, node.w_t = w_d, w_a, w_t
    node.scoring_mode = scoring_mode
    node.get_robot_pose = lambda: robot_xy

    captured = {}

    def capture_markers(candidates, scores_, best_idx):
        captured['candidates'] = candidates
        captured['scores'] = np.asarray(scores_, dtype=float)
        captured['best_idx'] = best_idx

    node.publish_markers = capture_markers
    node.publish_goal = lambda best: captured.update(goal=best)
    node.clear_markers = lambda: None
    node.complete_pub.publish = lambda msg: captured.update(complete=True)

    node.process_map(make_grid(array, resolution, origin))

    if 'candidates' not in captured:
        return None, None, None
    return captured['candidates'], captured['scores'], captured['best_idx']


def shutdown():
    global _NODE
    if _NODE is not None:
        _NODE.destroy_node()
        _NODE = None
    if rclpy.ok():
        rclpy.shutdown()
