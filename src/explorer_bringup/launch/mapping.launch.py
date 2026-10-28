"""
Hardware mapping: the real robot (robot.launch.py: ESP32 bridge, EKF, X2 LiDAR) + SLAM
Toolbox, and RViz if wanted. No Nav2, no exploration: drive by hand and the map builds.

    ros2 launch explorer_bringup mapping.launch.py esp_port:=/dev/serial/by-path/... \
        lidar_port:=/dev/serial/by-path/...          # rviz:=true on a machine with a screen
    ros2 run explorer_exploration manual_drive --ros-args -p topic:=/cmd_vel   # drive (w a s d x)
    ros2 run nav2_map_server map_saver_cli -f ~/map  # save the map

Without hardware: ros2 run explorer_bringup fake_robot, then
    esp_port:=socket://localhost:47001 lidar_port:=socket://localhost:47002
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition
from launch.events import matches_action
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition

BRINGUP = get_package_share_directory('explorer_bringup')


def generate_launch_description():
    slam = LifecycleNode(
        package='slam_toolbox', executable='sync_slam_toolbox_node', name='slam_toolbox',
        namespace='', output='screen',
        parameters=[os.path.join(BRINGUP, 'config', 'slam.yaml'), {'use_sim_time': False}])
    # SLAM Toolbox is a lifecycle node: configure it at start, activate it once configured
    configure = EmitEvent(event=ChangeState(lifecycle_node_matcher=matches_action(slam),
                                            transition_id=Transition.TRANSITION_CONFIGURE))
    activate = RegisterEventHandler(OnStateTransition(
        target_lifecycle_node=slam, start_state='configuring', goal_state='inactive',
        entities=[EmitEvent(event=ChangeState(lifecycle_node_matcher=matches_action(slam),
                                              transition_id=Transition.TRANSITION_ACTIVATE))]))

    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='false'),
        # esp_port, lidar_port, lidar and mock pass through to robot.launch.py
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(BRINGUP, 'launch', 'robot.launch.py'))),
        slam, configure, activate,
        Node(package='rviz2', executable='rviz2', output='log',
             arguments=['-d', os.path.join(BRINGUP, 'config', 'mapping.rviz')],
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
