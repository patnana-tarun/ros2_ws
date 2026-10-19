#!/usr/bin/env python3
"""Turn-rate step test on the simulated robot (no Nav2): publish in-place TwistStamped yaw-rate
steps on /cmd_vel and measure the true yaw rate from Gazebo's pose. Usage: turn_step_test.py OUT.json"""
import sys, time, math, json, threading
import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from gz.transport13 import Node as GzNode
from gz.msgs10.pose_v_pb2 import Pose_V

STEPS = [0.1, 0.2, 0.3, 0.45, 0.6, -0.3, -0.6]
rclpy.init(); n = Node('turn_step_test'); pub = n.create_publisher(TwistStamped, 'cmd_vel', 10)
lock = threading.Lock(); log = []
def on_pose(msg):
    for p in msg.pose:
        if p.name == 'explorer':
            q = p.orientation
            with lock: log.append((time.time(), math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))))
gz = GzNode(); gz.subscribe(Pose_V, '/world/cave/dynamic_pose/info', on_pose)
def send(wz, dur):
    t0 = time.time()
    while time.time() - t0 < dur:
        m = TwistStamped(); m.header.stamp = n.get_clock().now().to_msg(); m.twist.angular.z = wz
        pub.publish(m); rclpy.spin_once(n, timeout_sec=0.02); time.sleep(0.03)
time.sleep(2); res = []
for wz in STEPS:
    send(wz, 6.0)
    with lock: L = [q for q in log if q[0] > time.time() - 3.0]   # last 3 s of the step (steady state)
    t = np.array([q[0] for q in L]); y = np.unwrap(np.array([q[1] for q in L]))
    rate = float(np.polyfit(t - t[0], y, 1)[0]) if len(t) > 5 else float('nan')
    res.append({'cmd': wz, 'true': rate, 'ratio': rate / wz}); print(f'cmd {wz:+.2f} rad/s -> true {rate:+.3f} rad/s  ratio {rate / wz:.2f}', flush=True)
    send(0.0, 2.0)
json.dump(res, open(sys.argv[1], 'w'))
