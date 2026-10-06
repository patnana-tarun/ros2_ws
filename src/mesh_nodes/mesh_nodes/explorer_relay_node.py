#!/usr/bin/env python3
"""
Explorer-side relay: forward /map and /tf onto the mesh from one process.

Behavior (fixed rates, no map-in-flight throttle):
  - Map: the latest /map is published every map_publish_period_sec (3 s),
    whether or not it changed since the last one, RELIABLE +
    TRANSIENT_LOCAL. A fixed period gives the receiver a known expected
    map count per window. The map heartbeat is also sent right after
    each map, so that count is exact rather than up to 1 s stale.
  - TF: 1 of every tf_decimation (3) /tf messages is forwarded, i.e. a
    third of the real tf rate. Counted per tf source (the set of child
    frames in the message), so each source keeps a third of its own
    rate; one shared counter over the mixed stream could alias and
    starve one source. Skipped messages use no sequence_id, so the
    receiver's expected count is already the forwarded third.
  - MeshTf.map_in_flight is kept in the message (changing it would break
    the receiver's interface) but is always False now.

Timers and transmission_stamp use wall time even with use_sim_time:=true.
Mesh airtime and the receiver's latency measurement are both wall-clock
quantities; sim time would make the publish and heartbeat rates depend
on Gazebo's real-time factor and give the receiver stamps it can't
compare against its own clock.
"""

import random

from my_mesh_interfaces.msg import MeshMap, MeshTf, SenderStatus
from nav_msgs.msg import OccupancyGrid
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from tf2_msgs.msg import TFMessage


class ExplorerRelayNode(Node):
    """Relay /map and /tf to /mesh/* with an envelope, at fixed reduced rates."""

    def __init__(self):
        super().__init__('explorer_relay_node')

        # ---- parameters ----
        self.declare_parameter('map_publish_period_sec', 3.0)
        self.declare_parameter('tf_decimation', 3)

        self.map_publish_period = max(
            0.1, float(self.get_parameter('map_publish_period_sec').value))
        self.tf_decimation = max(1, int(self.get_parameter('tf_decimation').value))

        self.get_logger().info(
            f'Map every {self.map_publish_period}s, '
            f'TF 1 of every {self.tf_decimation} messages')

        # ---- clocks: wall time regardless of use_sim_time (see module doc) ----
        self._stamp_clock = Clock(clock_type=ClockType.SYSTEM_TIME)
        self._timer_clock = Clock(clock_type=ClockType.STEADY_TIME)

        # ---- shared session for this node's lifetime ----
        self.session_id = random.getrandbits(63)
        self.map_sequence_counter = 0
        self.tf_sequence_counter = 0

        # ---- latest /map, sent on the map timer ----
        self._latest_map = None

        # ---- tf decimation: messages seen per tf source ----
        self._tf_seen = {}

        # ==================== MAP side ====================
        map_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self.raw_map_sub = self.create_subscription(
            OccupancyGrid, '/map', self.map_callback, map_qos)
        self.mesh_map_pub = self.create_publisher(
            MeshMap, '/mesh/map', map_qos)
        self.map_status_pub = self.create_publisher(
            SenderStatus, '/mesh/map_status', 10)
        self.create_timer(1.0, self.publish_map_status, clock=self._timer_clock)
        self.create_timer(self.map_publish_period, self.publish_map,
                          clock=self._timer_clock)

        # ==================== TF side ====================
        # BEST_EFFORT, not RELIABLE: tf is high-rate and self-healing (a
        # dropped sample is corrected by the next one, see tf_callback
        # below), so paying for DDS retransmission on a lossy mesh link
        # just adds latency/airtime for no real benefit. RELIABLE stays
        # reserved for map, where a lost packet has no "next sample" to
        # fix it. Must match the receiver's mesh_sub QoS (tf_rolling_
        # metrics_node.py) -- a RELIABLE subscriber can't connect to a
        # BEST_EFFORT publisher in DDS.
        tf_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=100,
        )
        self.raw_tf_sub = self.create_subscription(
            TFMessage, '/tf', self.tf_callback, tf_qos)
        self.mesh_tf_pub = self.create_publisher(
            MeshTf, '/mesh/tf', tf_qos)
        self.tf_status_pub = self.create_publisher(
            SenderStatus, '/mesh/tf_status', 10)
        # 5Hz, not 1Hz: the receiver's rolling-window PDR expected-count
        # is derived from these heartbeats (see _expected_over_span in
        # tf_rolling_metrics_node.py). With a 1s heartbeat a rolling
        # window edge could use a sample stale by up to ~1s, over/under-
        # estimating "expected" (seen in practice while the old map
        # throttle switched on and off within a second). SenderStatus is
        # two uint64s; 5Hz adds negligible airtime.
        self.create_timer(0.2, self.publish_tf_status, clock=self._timer_clock)

        self.get_logger().info(
            f'Explorer Relay Node initialized. session_id={self.session_id}')

    # ------------------------------------------------------------------
    def map_callback(self, raw_msg: OccupancyGrid):
        """Keep the latest /map; publish_map sends it on a fixed period."""
        self._latest_map = raw_msg

    def publish_map(self):
        """Wrap the latest /map in the envelope and publish it."""
        if self._latest_map is None:
            return
        self.map_sequence_counter += 1

        mesh_msg = MeshMap()
        mesh_msg.session_id = self.session_id
        mesh_msg.sequence_id = self.map_sequence_counter
        mesh_msg.map_data = self._latest_map
        mesh_msg.transmission_stamp = self._stamp_clock.now().to_msg()

        self.mesh_map_pub.publish(mesh_msg)
        # Heartbeat straight away, so the receiver's expected map count
        # includes this map as soon as it could have arrived.
        self.publish_map_status()

    def publish_map_status(self):
        """Publish the map heartbeat (session + last map sequence sent)."""
        status = SenderStatus()
        status.session_id = self.session_id
        status.last_sequence_sent = self.map_sequence_counter
        self.map_status_pub.publish(status)

    # ------------------------------------------------------------------
    def tf_callback(self, raw_msg: TFMessage):
        """Forward 1 of every tf_decimation /tf messages per tf source."""
        source = tuple(sorted(t.child_frame_id for t in raw_msg.transforms))
        seen = self._tf_seen.get(source, 0)
        self._tf_seen[source] = seen + 1
        if seen % self.tf_decimation != 0:
            # Skipped on purpose, not a loss: tf self-heals via the next
            # forwarded sample, and no sequence_id is used.
            return

        self.tf_sequence_counter += 1

        mesh_msg = MeshTf()
        mesh_msg.session_id = self.session_id
        mesh_msg.sequence_id = self.tf_sequence_counter
        mesh_msg.tf_data = raw_msg
        mesh_msg.transmission_stamp = self._stamp_clock.now().to_msg()
        mesh_msg.map_in_flight = False  # throttle removed; field kept for the interface

        self.mesh_tf_pub.publish(mesh_msg)

    def publish_tf_status(self):
        """Publish the TF heartbeat (session + last TF sequence sent)."""
        status = SenderStatus()
        status.session_id = self.session_id
        status.last_sequence_sent = self.tf_sequence_counter
        self.tf_status_pub.publish(status)


def main(args=None):
    rclpy.init(args=args)
    node = ExplorerRelayNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        # try_shutdown: on Ctrl+C the SIGINT handler has usually shut the
        # context down already, and a second rclpy.shutdown() raises.
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
