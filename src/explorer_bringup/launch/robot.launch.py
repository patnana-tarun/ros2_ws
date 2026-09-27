"""
Real explorer robot, on the Raspberry Pi: robot_state_publisher + motor/encoder driver +
MPU-9250 + YDLIDAR X2 + the wheel/IMU EKF. Provides the same topics and TF as
explorer_description's Gazebo launch, so SLAM, Nav2 and exploration run unchanged:

    ros2 launch explorer_exploration bringup.launch.py sim:=false     # everything
    ros2 launch explorer_bringup robot.launch.py                      # robot only
    ros2 launch explorer_bringup robot.launch.py mock:=true           # no hardware (test)

The LiDAR needs ydlidar_ros2_driver (built from source with the YDLidar-SDK; not
packaged for Jazzy). If it is not installed, a warning is printed and the rest starts.
"""
import os

from ament_index_python.packages import (PackageNotFoundError,
                                         get_package_share_directory)
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

DESC = get_package_share_directory('explorer_description')
BRINGUP = get_package_share_directory('explorer_bringup')


def generate_launch_description():
    mock = ParameterValue(LaunchConfiguration('mock'), value_type=bool)
    robot_yaml = os.path.join(BRINGUP, 'config', 'robot.yaml')

    try:
        get_package_share_directory('ydlidar_ros2_driver')
        # YDLIDAR X2 settings - check against the driver's params/X2.yaml for your version
        lidar = Node(
            package='ydlidar_ros2_driver',
            executable='ydlidar_ros2_driver_node',
            name='ydlidar_ros2_driver_node',
            output='screen',
            parameters=[{
                'port': LaunchConfiguration('lidar_port'),
                'frame_id': 'laser_frame',
                'baudrate': 115200,
                'lidar_type': 1,            # triangle
                'device_type': 0,           # serial
                'isSingleChannel': True,
                'intensity': False,
                'support_motor_dtr': True,
                'sample_rate': 3,
                'frequency': 7.0,
                'angle_min': -180.0,
                'angle_max': 180.0,
                'range_min': 0.12,
                'range_max': 8.0,
                'reversion': False,
                'inverted': True,
                'auto_reconnect': True,
                'fixed_resolution': True,
                'invalid_range_is_inf': True,
            }],
            remappings=[('scan', '/scan')],
        )
    except PackageNotFoundError:
        lidar = LogInfo(msg='[robot.launch] ydlidar_ros2_driver not installed - no /scan. '
                            'Build it from source (YDLidar-SDK + ydlidar_ros2_driver).')

    return LaunchDescription([
        DeclareLaunchArgument('mock', default_value='false',
                              description='true = no GPIO/I2C (test the software anywhere)'),
        DeclareLaunchArgument('lidar_port', default_value='/dev/ttyUSB0'),

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
            executable='explorer_base',
            parameters=[robot_yaml, {'mock': mock}],
            output='screen',
        ),
        Node(
            package='explorer_bringup',
            executable='mpu9250_imu',
            parameters=[robot_yaml, {'mock': mock}],
            output='screen',
        ),
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            parameters=[os.path.join(DESC, 'config', 'ekf.yaml')],
            remappings=[('odometry/filtered', 'odom')],
            output='screen',
        ),
        lidar,
    ])
