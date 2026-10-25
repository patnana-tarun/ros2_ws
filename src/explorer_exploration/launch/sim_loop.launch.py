"""
Endless simulation for testing the mesh relay: explore the cave, and at 85 % coverage shut the sim
down and start a fresh one, until Ctrl-C. The relay runs once for the whole session (one
session_id, sequence numbers continue across restarts); only the sim restarts.

    ros2 launch explorer_exploration sim_loop.launch.py
    ros2 launch explorer_exploration sim_loop.launch.py sim_args:='rviz:=false'
    ros2 launch explorer_exploration sim_loop.launch.py target_pct:=90 relay:=false

Restarts and their reasons go to ~/.ros/sim_loop_cycles.csv (one row per run, wall-clock start
and end), so the restart gaps (~30 s without /map and /tf) can be cut out of the metrics.
Details: explorer_exploration/sim_loop.py.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    relay_params = os.path.join(
        get_package_share_directory('mesh_nodes'), 'config', 'explorer_relay.yaml')
    lc = LaunchConfiguration

    return LaunchDescription([
        DeclareLaunchArgument('sim_launch', default_value='tunnel_reverse.launch.py',
                              description='explorer_exploration launch file restarted each run'),
        DeclareLaunchArgument('sim_args', default_value='',
                              description="arguments for sim_launch, e.g. 'rviz:=false gui:=false'"),
        DeclareLaunchArgument('target_pct', default_value='85.0',
                              description='true-floor coverage (%) that ends a run'),
        DeclareLaunchArgument('stall_restart_s', default_value='300.0',
                              description='restart when < 0.5 m2 new floor in this many s (0 = never)'),
        DeclareLaunchArgument('relay', default_value='true',
                              description='also run the mesh relay (explorer_relay_node)'),
        DeclareLaunchArgument('cycle_log',
                              default_value=os.path.expanduser('~/.ros/sim_loop_cycles.csv'),
                              description='CSV with one row per run'),
        Node(
            package='explorer_exploration',
            executable='sim_loop',
            name='sim_loop',
            output='screen',
            parameters=[{
                'sim_launch': lc('sim_launch'),
                'sim_args': ParameterValue(lc('sim_args'), value_type=str),
                'target_pct': ParameterValue(lc('target_pct'), value_type=float),
                'stall_restart_s': ParameterValue(lc('stall_restart_s'), value_type=float),
                'cycle_log': lc('cycle_log'),
            }],
        ),
        # wall-clock timers and stamps (see the relay's module doc), so no sim time: the sim
        # clock jumps back to 0 on every restart
        Node(
            package='mesh_nodes',
            executable='explorer_relay',
            name='explorer_relay_node',
            output='screen',
            parameters=[relay_params, {'use_sim_time': False}],
            condition=IfCondition(lc('relay')),
        ),
    ])
