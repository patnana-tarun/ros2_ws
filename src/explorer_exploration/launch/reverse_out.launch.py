"""
Reverse-out navigation (confirmed 2026-10-20, docs/issues/Reverse-out 2026-10-20.md).

Starts the normal bringup.launch.py with the reverse-out set-up, so it can be run with one
command while bringup.launch.py itself keeps its defaults:

    ros2 launch explorer_exploration reverse_out.launch.py            # GUI, cave
    ros2 launch explorer_exploration reverse_out.launch.py rviz:=false

What it sets (every other bringup argument passes through unchanged):
  params_file          config/nav2_params_reverse.yaml  (MPPI may follow the path backwards:
                       PathAngleCritic mode 1, PreferForward weight 2, vx_min -0.15)
  bt_xml               explore_nav_to_pose_demo.xml     (path smoothing in place)
  precheck_path        true   (refuse frontiers with no explored route before sending them)
  publish_explored_map true   (the global costmap plans only through explored space)
  stall_timeout        30.0   (give up on a goal after 30 s without 0.3 m of progress)
  skid_track           0.38   (sim only: Gazebo DiffDrive effective track width)
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

PKG_SHARE = get_package_share_directory('explorer_exploration')


def generate_launch_description():
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(PKG_SHARE, 'launch', 'bringup.launch.py')),
            launch_arguments={
                'params_file': os.path.join(PKG_SHARE, 'config', 'nav2_params_reverse.yaml'),
                'bt_xml': 'explore_nav_to_pose_demo.xml',
                'precheck_path': 'true',
                'publish_explored_map': 'true',
                'stall_timeout': '30.0',
                'skid_track': '0.38',
            }.items(),
        ),
    ])
