"""
Tunnel-reverse navigation (exp/tunnel-tracking line, 2026-10-20; user's request): reverse allowed
only inside tunnels; in open space the robot drives forward and turns round as usual.

    ros2 launch explorer_exploration tunnel_reverse.launch.py            # GUI, cave
    ros2 launch explorer_exploration tunnel_reverse.launch.py rviz:=false

Same as reverse_out.launch.py, except:
  params_file  config/nav2_params_tunnel_reverse.yaml: two MPPI controllers, FollowPath (forward
               preferred) and FollowPathReverse (the reverse-out settings)
  + drive_mode_switcher: picks FollowPathReverse when the LiDAR sees a passage narrower than
    1.2 m and FollowPath when it is wider than 1.8 m (1 s of consistent readings), through the
    BT's ControllerSelector on /controller_selector.
  + planner plans for a round robot of radius 0.22 m (gaps under ~0.45 m are not planned through)
  + retrace: stuck in a tunnel -> back out 1 m along the robot's own track
bringup.launch.py keeps its defaults.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

PKG_SHARE = get_package_share_directory('explorer_exploration')


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('tunnel_width', default_value='1.2',
                              description='passage narrower than this (m) = tunnel: reverse allowed'),
        DeclareLaunchArgument('open_width', default_value='1.8',
                              description='passage wider than this (m) = open space: forward driving'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(PKG_SHARE, 'launch', 'bringup.launch.py')),
            launch_arguments={
                'params_file': os.path.join(PKG_SHARE, 'config', 'nav2_params_tunnel_reverse.yaml'),
                'bt_xml': 'explore_nav_to_pose_demo.xml',
                'precheck_path': 'true',
                'publish_explored_map': 'true',
                'stall_timeout': '30.0',
                'skid_track': '0.38',
                'stall_angle': '0.5',      # a U-turn on the spot is progress, not a stall
                # stuck in a tunnel: back out 1 m along the own track (known free)
                'retrace_distance': '1.0',
                'retrace_controller': 'FollowPathReverse',
                # nav-speed: a frontier behind the robot must be worth a U-turn; without it every
                # start-up was two U-turns within a minute (a >= 300 deg rotation event)
                'heading_weight': '1.0',
            }.items(),
        ),
        Node(
            package='explorer_exploration',
            executable='drive_mode_switcher',
            name='drive_mode_switcher',
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'tunnel_width': ParameterValue(LaunchConfiguration('tunnel_width'), value_type=float),
                'open_width': ParameterValue(LaunchConfiguration('open_width'), value_type=float),
            }],
        ),
    ])
