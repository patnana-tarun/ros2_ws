"""
Launch the explorer-side mesh relay.

    ros2 launch mesh_nodes explorer_relay.launch.py
    ros2 launch mesh_nodes explorer_relay.launch.py params_file:=/path/to/other.yaml
    ros2 launch mesh_nodes explorer_relay.launch.py use_sim_time:=true   # with Gazebo
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory('mesh_nodes'), 'config', 'explorer_relay.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=default_params,
                              description='YAML file with explorer_relay_node parameters'),
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='Use /clock (true when running in Gazebo)'),
        Node(
            package='mesh_nodes',
            executable='explorer_relay',
            name='explorer_relay_node',
            parameters=[LaunchConfiguration('params_file'),
                        {'use_sim_time': LaunchConfiguration('use_sim_time')}],
            output='screen',
        ),
    ])
