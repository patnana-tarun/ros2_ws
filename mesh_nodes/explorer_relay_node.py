#!/usr/bin/env python3
"""
Explorer-side relay node: publishes BOTH /map and /tf onto the mesh from
a single process, since both originate from the same robot. This lets
the map-in-flight signal be a plain in-process flag -- no extra topic,
no risk of that signal itself being lost on a lossy mesh.

Behavior:
  - Map: forwarded on every /map publish, RELIABLE + TRANSIENT_LOCAL,
    unchanged from the earlier map relay. Right before publish(), sets
    self.map_in_flight = True; a one-shot timer clears it back to False
    after map_in_flight_hold_sec (a fixed approximation of mesh clear
    time -- see notes below on why fixed vs. dynamic).
  - TF: forwarded on every /tf publish UNLESS map_in_flight is True, in
    which case only tf_throttle_send out of every tf_throttle_total
    consecutive messages are forwarded (default 2-in-5). This trades a
    temporary reduction in tf freshness for more mesh airtime for the
    map, during exactly the window it's competing for the channel.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from nav_msgs.msg import OccupancyGrid
from tf2_msgs.msg import TFMessage

from my_mesh_interfaces.msg import MeshMap, MeshTf, SenderStatus

import random


class ExplorerRelayNode(Node):
    def __init__(self):
        super().__init__('explorer_relay_node')

        # ---- parameters ----
        self.declare_parameter('tf_throttle_send', 2)
        self.declare_parameter('tf_throttle_total', 5)
        self.declare_parameter('map_in_flight_hold_sec', 2.0)

        self.tf_throttle_send = max(
            1, int(self.get_parameter('tf_throttle_send').value))
        self.tf_throttle_total = max(
            self.tf_throttle_send, int(self.get_parameter('tf_throttle_total').value))
        self.map_in_flight_hold_sec = max(
            0.0, float(self.get_parameter('map_in_flight_hold_sec').value))

        self.get_logger().info(
            f'TF throttle ratio during map transmission: '
            f'{self.tf_throttle_send}/{self.tf_throttle_total}, '
            f'map_in_flight_hold_sec={self.map_in_flight_hold_sec}')

        # ---- shared session for this node's lifetime ----
        self.session_id = random.getrandbits(63)
        self.map_sequence_counter = 0
        self.tf_sequence_counter = 0

        # ---- in-flight flag, cleared by a one-shot timer per map publish ----
        self.map_in_flight = False
        self._map_in_flight_timer = None

        # ---- tf throttle counter (counts messages seen while throttling active) ----
        self._tf_throttle_counter = 0

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
        self.create_timer(1.0, self.publish_map_status)

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
        # tf_rolling_metrics_node.py). A 1s heartbeat is coarse next to
        # the throttle gate, which can flip state well inside a second --
        # a rolling window straddling that transition could pick a
        # heartbeat sample stale by up to ~1s, over/under-estimating
        # "expected" right at the edges. Seen in practice as PDR
        # oscillating with throttle_active_fraction instead of degrading
        # smoothly, while tq (an independent, non-heartbeat-based signal)
        # stayed flat -- i.e. the dips tracked measurement quantization,
        # not the link. SenderStatus is two uint64s; 5Hz adds negligible
        # airtime.
        self.create_timer(0.2, self.publish_tf_status)

        self.get_logger().info(
            f'Explorer Relay Node initialized. session_id={self.session_id}')

    # ------------------------------------------------------------------
    def map_callback(self, raw_msg: OccupancyGrid):
        self.map_sequence_counter += 1

        mesh_msg = MeshMap()
        mesh_msg.session_id = self.session_id
        mesh_msg.sequence_id = self.map_sequence_counter
        mesh_msg.map_data = raw_msg
        mesh_msg.transmission_stamp = self.get_clock().now().to_msg()

        self.mesh_map_pub.publish(mesh_msg)

        # Mark map as "in flight" and (re)arm the timer that clears it.
        # A fixed hold time is a deliberate simplification: we don't have
        # a delivery ACK back from the receiver at this layer, so we
        # approximate "long enough for this map to likely clear the
        # mesh" rather than waiting for confirmed delivery. Tune
        # map_in_flight_hold_sec against your own observed map latency
        # (e.g. ~2x your typical map transmission_stamp-to-receive delay).
        self.map_in_flight = True
        if self._map_in_flight_timer is not None:
            self.destroy_timer(self._map_in_flight_timer)
        self._map_in_flight_timer = self.create_timer(
            self.map_in_flight_hold_sec, self._clear_map_in_flight)

    def _clear_map_in_flight(self):
        self.map_in_flight = False
        if self._map_in_flight_timer is not None:
            self.destroy_timer(self._map_in_flight_timer)
            self._map_in_flight_timer = None

    def publish_map_status(self):
        status = SenderStatus()
        status.session_id = self.session_id
        status.last_sequence_sent = self.map_sequence_counter
        self.map_status_pub.publish(status)

    # ------------------------------------------------------------------
    def tf_callback(self, raw_msg: TFMessage):
        if self.map_in_flight:
            # Throttled mode: forward tf_throttle_send out of every
            # tf_throttle_total consecutive messages. Counter resets
            # naturally once map_in_flight goes False (see below).
            self._tf_throttle_counter += 1
            slot = ((self._tf_throttle_counter - 1) % self.tf_throttle_total)
            if slot >= self.tf_throttle_send:
                return  # dropped intentionally, not a loss -- self-heals
                        # via the next forwarded tf sample, per earlier
                        # discussion of tf being self-correcting
        else:
            # Not throttling right now -- reset the counter so the next
            # throttled period starts cleanly at slot 0, not mid-cycle.
            self._tf_throttle_counter = 0

        self.tf_sequence_counter += 1

        mesh_msg = MeshTf()
        mesh_msg.session_id = self.session_id
        mesh_msg.sequence_id = self.tf_sequence_counter
        mesh_msg.tf_data = raw_msg
        mesh_msg.transmission_stamp = self.get_clock().now().to_msg()
        # Explicit signal, not a rate-based heuristic: was this sample one
        # of the throttled 2-of-5 sent while a map transfer was in flight.
        mesh_msg.map_in_flight = self.map_in_flight

        self.mesh_tf_pub.publish(mesh_msg)

    def publish_tf_status(self):
        status = SenderStatus()
        status.session_id = self.session_id
        status.last_sequence_sent = self.tf_sequence_counter
        self.tf_status_pub.publish(status)


def main(args=None):
    rclpy.init(args=args)
    node = ExplorerRelayNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
