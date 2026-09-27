"""
Motor + encoder driver for the real explorer robot, run on the Raspberry Pi.

    ros2 run explorer_bringup explorer_base --ros-args --params-file config/robot.yaml
    ros2 run explorer_bringup explorer_base --ros-args -p mock:=true     # no hardware

Hardware (user, 2026-09-26):
  - 6 BO motors, 200 RPM, driven by 3 TB6612FNG dual drivers - one per axle
    (front, middle, rear), channel A = left wheel, channel B = right wheel.
  - LM393 slot encoders with 20-slot disks on the 4 corner wheels (front and rear),
    not the middle ones. They are single-channel: they count slots but cannot tell
    direction, so the direction is taken from the commanded motor direction.

In:  /cmd_vel (geometry_msgs/TwistStamped)
Out: /wheel/odom (nav_msgs/Odometry, twist used by the EKF), /joint_states (wheel angles,
     so robot_state_publisher can place the wheel links)

Skid-steer kinematics use an *effective* track width (track_width, default 0.43 m, the
value calibrated in simulation), not the geometric 0.176 m: the wheels slide sideways when
the robot turns. Calibrate it on the real robot: command a turn rate, measure the actual
rate (IMU), and scale track_width by commanded/actual.

GPIO access uses lgpio (sudo apt install python3-lgpio), which works on Pi 4 and Pi 5.
With mock:=true no GPIO is touched and the encoders are simulated from the commands.
"""

import math
import threading

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import JointState

WHEELS = ['left_front', 'left_middle', 'left_rear', 'right_front', 'right_middle', 'right_rear']
ENCODED = ['left_front', 'left_rear', 'right_front', 'right_rear']


def side_of(wheel):
    return 'left' if wheel.startswith('left') else 'right'


class Motors:
    """Six motors on three TB6612FNG. duty in [-1, 1] per side.

    Wheels on the same side may share their IN1/IN2/PWM pins (a skid-steer always drives
    a side's wheels alike), so every distinct pin is claimed and written once."""

    def __init__(self, node, h, pins, pwm_hz, invert):
        self.node, self.h, self.pins, self.pwm_hz, self.invert = node, h, pins, pwm_hz, invert
        self.warned = False
        if h is None:
            return
        import lgpio
        self.lg = lgpio
        for pin in {pins[w][k] for w in WHEELS for k in ('in1', 'in2', 'pwm')}:
            lgpio.gpio_claim_output(h, pin, 0)
        for pin in set(pins['stby']):
            lgpio.gpio_claim_output(h, pin, 1)      # drivers enabled

    def levels(self, duty_left, duty_right):
        """{pin: value} for the direction pins and {pin: duty %} for the PWM pins."""
        out, pwm = {}, {}
        for wheel in WHEELS:
            duty = duty_left if side_of(wheel) == 'left' else duty_right
            if wheel in self.invert:
                duty = -duty
            p = self.pins[wheel]
            # TB6612: IN1=1 IN2=0 forward, IN1=0 IN2=1 reverse, both 0 = coast
            want = {p['in1']: 1 if duty > 0 else 0, p['in2']: 1 if duty < 0 else 0}
            for pin, v in want.items():
                if out.setdefault(pin, v) != v and not self.warned:
                    self.warned = True
                    self.node.get_logger().error(
                        f'GPIO {pin} is shared by wheels that need opposite directions - '
                        'an inverted wheel cannot share IN pins with a non-inverted one')
            pwm[p['pwm']] = min(abs(duty), 1.0) * 100.0
        return out, pwm

    def set(self, duty_left, duty_right):
        out, pwm = self.levels(duty_left, duty_right)
        if self.h is None:
            return
        for pin, v in out.items():
            self.lg.gpio_write(self.h, pin, v)
        for pin, d in pwm.items():
            self.lg.tx_pwm(self.h, pin, self.pwm_hz, d)

    def stop(self):
        self.set(0.0, 0.0)
        if self.h is not None:
            for pin in self.pins['stby']:
                self.lg.gpio_write(self.h, pin, 0)   # drivers in standby


class Encoders:
    """Counts slots on the 4 corner wheels (rising edges, via lgpio alerts)."""

    def __init__(self, h, pins, debounce_us):
        self.counts = {w: 0 for w in ENCODED}
        self.lock = threading.Lock()
        self.callbacks = []
        if h is None:
            return
        import lgpio
        for wheel in ENCODED:
            pin = pins[wheel]
            lgpio.gpio_claim_alert(h, pin, lgpio.RISING_EDGE, lgpio.SET_PULL_UP)
            lgpio.gpio_set_debounce_micros(h, pin, debounce_us)
            self.callbacks.append(lgpio.callback(h, pin, lgpio.RISING_EDGE, self._make_cb(wheel)))

    def _make_cb(self, wheel):
        def cb(chip, gpio, level, tick):
            with self.lock:
                self.counts[wheel] += 1
        return cb

    def take(self):
        """Counts since the last call, per encoded wheel."""
        with self.lock:
            c = dict(self.counts)
            for w in self.counts:
                self.counts[w] = 0
        return c


class ExplorerBase(Node):
    def __init__(self):
        super().__init__('explorer_base')
        p = self.declare_parameter
        p('mock', False)
        p('wheel_radius', 0.0325)
        p('track_width', 0.43)            # effective, see module docstring
        p('slots_per_rev', 20)
        p('max_wheel_rpm', 200.0)         # at the supply voltage in use
        p('min_duty', 0.25)               # below this BO motors don't turn
        p('kp', 1.5)                      # duty per (m/s) of speed error
        p('ki', 3.0)
        p('cmd_timeout', 0.5)             # s without /cmd_vel -> stop
        p('rate', 20.0)                   # control / odometry Hz
        p('speed_window', 0.25)           # s of encoder counts per speed estimate
        p('pwm_hz', 1000)
        p('debounce_us', 300)
        p('invert', [''])                 # wheels whose motor runs backwards
        # BCM pin numbers. The defaults are only an example wiring - set them to yours
        # (config/robot.yaml). Example: each side's three wheels share IN1/IN2/PWM, and
        # the three STBY lines share one pin; wiring every wheel separately would need
        # 25 GPIOs, including the UART, SPI and ID-EEPROM pins.
        p('stby', [4, 4, 4])
        for wheel in WHEELS:
            in1, in2, pwm = (5, 6, 12) if side_of(wheel) == 'left' else (23, 24, 13)
            p(f'{wheel}.in1', in1)
            p(f'{wheel}.in2', in2)
            p(f'{wheel}.pwm', pwm)
        for wheel, pin in zip(ENCODED, [17, 27, 22, 16]):
            p(f'encoder.{wheel}', pin)

        g = lambda name: self.get_parameter(name).value
        self.mock = g('mock')
        self.r, self.track = g('wheel_radius'), g('track_width')
        self.m_per_count = 2 * math.pi * self.r / g('slots_per_rev')
        self.v_max = g('max_wheel_rpm') / 60.0 * 2 * math.pi * self.r
        self.min_duty, self.kp, self.ki = g('min_duty'), g('kp'), g('ki')
        self.cmd_timeout, self.dt = g('cmd_timeout'), 1.0 / g('rate')
        self.window = max(1, int(round(g('speed_window') / self.dt)))

        pins = {w: {k: g(f'{w}.{k}') for k in ('in1', 'in2', 'pwm')} for w in WHEELS}
        pins['stby'] = list(g('stby'))
        enc_pins = {w: g(f'encoder.{w}') for w in ENCODED}
        # A pin may be shared only by the same signal (e.g. all left IN1s), never by two
        roles = {}
        for w in WHEELS:
            for k, pin in pins[w].items():
                roles.setdefault(pin, set()).add(f'{side_of(w)}.{k}')
        for pin in pins['stby']:
            roles.setdefault(pin, set()).add('stby')
        for w, pin in enc_pins.items():
            roles.setdefault(pin, set()).add(f'encoder.{w}')
        clash = {pin: r for pin, r in roles.items() if len(r) > 1}
        if clash:
            raise SystemExit(f'explorer_base: GPIO pins used for two different signals: {clash}')
        if {2, 3} & set(roles):
            raise SystemExit('explorer_base: GPIO 2/3 are the I2C bus used by the IMU')

        self.h = None
        if not self.mock:
            import lgpio
            self.h = lgpio.gpiochip_open(0)
        self.motors = Motors(self, self.h, pins, g('pwm_hz'), set(g('invert')))
        self.encoders = Encoders(self.h, enc_pins, g('debounce_us'))

        self.target = (0.0, 0.0)                  # commanded left/right wheel speed (m/s)
        self.last_cmd = None
        self.direction = {'left': 1, 'right': 1}  # sign applied to encoder counts
        self.integral = {'left': 0.0, 'right': 0.0}
        self.history = []                         # recent per-side distances
        self.angle = {w: 0.0 for w in WHEELS}
        self.x = self.y = self.th = 0.0

        self.create_subscription(TwistStamped, 'cmd_vel', self.cmd_cb, 10)
        self.odom_pub = self.create_publisher(Odometry, 'wheel/odom', 10)
        self.js_pub = self.create_publisher(JointState, 'joint_states', 10)
        self.create_timer(self.dt, self.update)
        self.get_logger().info(
            f"explorer_base started ({'MOCK - no hardware' if self.mock else 'GPIO'}), "
            f'track {self.track} m, {self.m_per_count * 1000:.1f} mm per encoder slot, '
            f'top wheel speed {self.v_max:.2f} m/s')

    def cmd_cb(self, msg):
        v, w = msg.twist.linear.x, msg.twist.angular.z
        self.target = (v - w * self.track / 2, v + w * self.track / 2)
        self.last_cmd = self.get_clock().now()

    def update(self):
        now = self.get_clock().now()
        if self.last_cmd is None or (now - self.last_cmd).nanoseconds / 1e9 > self.cmd_timeout:
            self.target = (0.0, 0.0)

        # --- encoders -> distance per side over this step
        if self.mock:
            counts = {w: abs(self.target[0 if side_of(w) == 'left' else 1]) * self.dt / self.m_per_count
                      for w in ENCODED}
        else:
            counts = self.encoders.take()
        dist = {}
        for side in ('left', 'right'):
            n = (counts[f'{side}_front'] + counts[f'{side}_rear']) / 2.0
            dist[side] = self.direction[side] * n * self.m_per_count
        self.history.append(dist)
        self.history = self.history[-self.window:]
        speed = {s: sum(h[s] for h in self.history) / (len(self.history) * self.dt) for s in dist}

        # --- speed control: feed-forward + PI per side
        duty = {}
        for side, target in zip(('left', 'right'), self.target):
            if abs(target) < 1e-3:
                duty[side] = 0.0
                self.integral[side] = 0.0
                continue
            self.direction[side] = 1 if target > 0 else -1     # single-channel encoders
            err = target - speed[side]
            self.integral[side] = max(-0.3, min(0.3, self.integral[side] + err * self.dt))
            d = target / self.v_max + self.kp * err + self.ki * self.integral[side]
            d = max(-1.0, min(1.0, d))
            if 0 < abs(d) < self.min_duty:
                d = math.copysign(self.min_duty, d)
            duty[side] = d
        self.motors.set(duty['left'], duty['right'])

        # --- odometry from this step's distances
        dl, dr = dist['left'], dist['right']
        ds, dth = (dl + dr) / 2, (dr - dl) / self.track
        self.x += ds * math.cos(self.th + dth / 2)
        self.y += ds * math.sin(self.th + dth / 2)
        self.th += dth
        for w in WHEELS:
            self.angle[w] += dist[side_of(w)] / self.r
        self.publish(now, (speed['left'] + speed['right']) / 2,
                     (speed['right'] - speed['left']) / self.track)

    def publish(self, now, vx, wz):
        o = Odometry()
        o.header.stamp = now.to_msg()
        o.header.frame_id = 'odom'
        o.child_frame_id = 'base_footprint'
        o.pose.pose.position.x, o.pose.pose.position.y = self.x, self.y
        o.pose.pose.orientation.z, o.pose.pose.orientation.w = math.sin(self.th / 2), math.cos(self.th / 2)
        o.twist.twist.linear.x = vx
        o.twist.twist.angular.z = wz
        pc = [0.0] * 36
        pc[0] = pc[7] = 0.05
        pc[14] = pc[21] = pc[28] = 1e3
        pc[35] = 0.5
        o.pose.covariance = pc
        tc = [0.0] * 36
        # vx from 20-slot encoders is coarse (10 mm per slot); vy = 0 is the skid-steer
        # constraint; wheel yaw rate is poor on a skid-steer (the EKF takes it from the IMU).
        tc[0], tc[7], tc[14], tc[21], tc[28], tc[35] = 0.01, 0.001, 1e3, 1e3, 1e3, 0.5
        o.twist.covariance = tc
        self.odom_pub.publish(o)

        js = JointState()
        js.header.stamp = o.header.stamp
        js.name = [f'{w}_wheel_joint' for w in WHEELS] + ['left_bogie_joint', 'right_bogie_joint']
        js.position = [self.angle[w] for w in WHEELS] + [0.0, 0.0]   # bogie angle not sensed
        self.js_pub.publish(js)

    def shutdown(self):
        self.motors.stop()
        if self.h is not None:
            import lgpio
            lgpio.gpiochip_close(self.h)


def main(args=None):
    rclpy.init(args=args)
    node = ExplorerBase()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
