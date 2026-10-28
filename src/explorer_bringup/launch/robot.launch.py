"""
Real explorer robot, on the Raspberry Pi: robot_state_publisher + ESP32 bridge (motors,
encoders, ICM-20948 IMU) + the wheel/IMU EKF + the YDLIDAR X2. Provides the same topics and
TF as explorer_description's Gazebo launch, so SLAM, Nav2 and exploration run unchanged:

    ros2 launch explorer_exploration bringup.launch.py sim:=false     # everything
    ros2 launch explorer_bringup robot.launch.py                      # robot only
    ros2 launch explorer_bringup robot.launch.py lidar:=none          # sensors without the LiDAR
    ros2 launch explorer_bringup robot.launch.py mock:=true           # no hardware (test)

Both the ESP32 and the X2 are USB serial devices, and /dev/ttyUSB0/1 can swap between boots.
Use the stable names in /dev/serial/by-path/ (one per USB socket):
    ros2 launch explorer_bringup robot.launch.py esp_port:=/dev/serial/by-path/... lidar_port:=...
lidar:=ydlidar uses ydlidar_ros2_driver instead of the built-in x2_lidar, if it is installed.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

DESC = get_package_share_directory('explorer_description')
ROBOT_YAML = os.path.join(get_package_share_directory('explorer_bringup'), 'config', 'robot.yaml')


def lidar(context):
    kind = LaunchConfiguration('lidar').perform(context)
    port = LaunchConfiguration('lidar_port').perform(context)
    if kind == 'none' or LaunchConfiguration('mock').perform(context) == 'true':
        return []
    if kind == 'ydlidar':
        return [Node(package='ydlidar_ros2_driver', executable='ydlidar_ros2_driver_node',
                     name='ydlidar_ros2_driver_node', output='screen',
                     parameters=[{'port': port, 'frame_id': 'laser_frame', 'baudrate': 115200,
                                  'lidar_type': 1, 'device_type': 0, 'isSingleChannel': True,
                                  'intensity': False, 'support_motor_dtr': True,
                                  'sample_rate': 3, 'frequency': 7.0, 'angle_min': -180.0,
                                  'angle_max': 180.0, 'range_min': 0.12, 'range_max': 8.0,
                                  'reversion': False, 'inverted': True, 'auto_reconnect': True,
                                  'fixed_resolution': True, 'invalid_range_is_inf': True}])]
    return [Node(package='explorer_bringup', executable='x2_lidar', output='screen',
                 parameters=[ROBOT_YAML, {'port': port}])]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('mock', default_value='false',
                              description='true = no hardware (simulated ESP32, no LiDAR)'),
        DeclareLaunchArgument('esp_port', default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument('lidar', default_value='x2', description='x2 | ydlidar | none'),
        DeclareLaunchArgument('lidar_port', default_value='/dev/ttyUSB1'),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': ParameterValue(
                Command(['xacro ', os.path.join(DESC, 'urdf', 'explorer.urdf.xacro')]),
                value_type=str)}],
            output='screen',
        ),
        Node(
            package='explorer_bringup',
            executable='esp32_bridge',
            parameters=[ROBOT_YAML, {
                'mock': ParameterValue(LaunchConfiguration('mock'), value_type=bool),
                'port': LaunchConfiguration('esp_port')}],
            output='screen',
        ),
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            # predict_to_current_time: publish every 30 Hz cycle. The ESP32's 50 Hz telemetry
            # leaves some cycles without a new measurement, and the EKF then skips them
            # (measured 20 Hz without it, 30 Hz with it). The sim keeps ekf.yaml as it is.
            parameters=[os.path.join(DESC, 'config', 'ekf.yaml'), {'predict_to_current_time': True}],
            remappings=[('odometry/filtered', 'odom')],
            output='screen',
        ),
        OpaqueFunction(function=lidar),
    ])
