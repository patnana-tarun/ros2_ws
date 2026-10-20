from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    w_distance = LaunchConfiguration('w_distance')
    w_adjacency = LaunchConfiguration('w_adjacency')
    w_trapezoid = LaunchConfiguration('w_trapezoid')
    min_frontier_size = LaunchConfiguration('min_frontier_size')
    sensor_short_range = LaunchConfiguration('sensor_short_range')
    sensor_long_range = LaunchConfiguration('sensor_long_range')
    scoring_mode = LaunchConfiguration('scoring_mode')
    unknown_gap_fill = LaunchConfiguration('unknown_gap_fill')
    selection_mode = LaunchConfiguration('selection_mode')
    precheck_path = LaunchConfiguration('precheck_path')
    stall_timeout = LaunchConfiguration('stall_timeout')
    stall_angle = LaunchConfiguration('stall_angle')
    publish_explored_map = LaunchConfiguration('publish_explored_map')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('w_distance', default_value='1.0'),
        DeclareLaunchArgument('w_adjacency', default_value='1.0'),
        DeclareLaunchArgument('w_trapezoid', default_value='1.0'),
        DeclareLaunchArgument('min_frontier_size', default_value='7'),
        # YDLIDAR X2 (0.12-8 m, reliable to ~6 m) - the paper's inner/outer
        # trapezoid bands (Eq. 5) are defined by these.
        DeclareLaunchArgument('sensor_short_range', default_value='0.5'),
        DeclareLaunchArgument('sensor_long_range', default_value='6.0'),
        # 'tad' (default) or 'nearest' (classic baseline, for A/B benchmarking).
        DeclareLaunchArgument('scoring_mode', default_value='tad'),
        # Fill unknown gaps between LiDAR rays before frontier detection
        # (0 = original behaviour). See frontier_tad_node.py.
        DeclareLaunchArgument('unknown_gap_fill', default_value='2'),
        # 'dfs' (finish the current branch first) or 'global' (original: best
        # TAD score anywhere). See frontier_tad_node.py.
        DeclareLaunchArgument('selection_mode', default_value='dfs'),
        # Ask the planner for a path before sending a frontier; blacklist it at once if
        # there is none. See explore_coordinator.py.
        DeclareLaunchArgument('precheck_path', default_value='false'),
        # Abandon a goal when the robot moved < 0.3 m in this many seconds (0 = off).
        # See explore_coordinator.py.
        DeclareLaunchArgument('stall_timeout', default_value='0.0'),
        DeclareLaunchArgument('stall_angle', default_value='0.0'),
        # Publish /map_explored (ray gaps filled) for a global costmap that plans only through
        # known space. See frontier_tad_node.py.
        DeclareLaunchArgument('publish_explored_map', default_value='false'),

        Node(
            package='explorer_exploration',
            executable='frontier_tad_node',
            name='frontier_tad_node',
            output='screen',
            parameters=[{
                'use_sim_time': ParameterValue(use_sim_time, value_type=bool),
                'w_distance': ParameterValue(w_distance, value_type=float),
                'w_adjacency': ParameterValue(w_adjacency, value_type=float),
                'w_trapezoid': ParameterValue(w_trapezoid, value_type=float),
                'min_frontier_size': ParameterValue(min_frontier_size, value_type=int),
                'sensor_short_range': ParameterValue(sensor_short_range, value_type=float),
                'sensor_long_range': ParameterValue(sensor_long_range, value_type=float),
                'scoring_mode': ParameterValue(scoring_mode, value_type=str),
                'unknown_gap_fill': ParameterValue(unknown_gap_fill, value_type=int),
                'selection_mode': ParameterValue(selection_mode, value_type=str),
                'publish_explored_map': ParameterValue(publish_explored_map, value_type=bool),
            }],
        ),
        Node(
            package='explorer_exploration',
            executable='explore_coordinator',
            name='explore_coordinator',
            output='screen',
            parameters=[{
                'use_sim_time': ParameterValue(use_sim_time, value_type=bool),
                'precheck_path': ParameterValue(precheck_path, value_type=bool),
                'stall_timeout': ParameterValue(stall_timeout, value_type=float),
                'stall_angle': ParameterValue(stall_angle, value_type=float),
            }],
        ),
    ])
