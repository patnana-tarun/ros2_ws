"""
Headless benchmark run: same stack as bringup.launch.py (Gazebo + Nav2 in slam:=True mode
+ our exploration package) but with no Gazebo window and no RViz2, and metrics_logger
added. For scripted A/B runs (scoring_mode:=tad vs scoring_mode:=nearest) without popping
GUI windows or needing a display for every run.

    ros2 launch explorer_exploration benchmark_headless.launch.py scoring_mode:=nearest

Ported from Humble: Gazebo Classic's gzserver chain is replaced by explorer_description's
launch with gui:=false (Gazebo Harmonic server with headless rendering, which the GPU
LiDAR still needs).
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    bringup_launch = os.path.join(
        get_package_share_directory('explorer_exploration'), 'launch', 'bringup.launch.py')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('scoring_mode', default_value='tad'),
        DeclareLaunchArgument('selection_mode', default_value='dfs'),
        DeclareLaunchArgument('world', default_value='cave.sdf'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(bringup_launch),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'world': LaunchConfiguration('world'),
                'x': LaunchConfiguration('x'),
                'y': LaunchConfiguration('y'),
                'gui': 'false',
                'rviz': 'false',
                'scoring_mode': LaunchConfiguration('scoring_mode'),
                'selection_mode': LaunchConfiguration('selection_mode'),
            }.items(),
        ),

        Node(
            package='explorer_exploration',
            executable='metrics_logger',
            name='metrics_logger',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
        ),
    ])
