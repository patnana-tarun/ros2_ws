"""
One-command bringup for testing (ROS 2 Jazzy, Gazebo Harmonic): the explorer robot in a
Gazebo world + SLAM Toolbox + Nav2 + our frontier/TAD exploration package + RViz2.

    ros2 launch explorer_exploration bringup.launch.py                   # cave.sdf
    ros2 launch explorer_exploration bringup.launch.py world:=cave_open.sdf
    ros2 launch explorer_exploration bringup.launch.py gui:=false rviz:=false
    ros2 launch explorer_exploration bringup.launch.py sim:=false rviz:=false   # real robot (Pi)

Ported from the Humble/TurtleBot3 version: turtlebot3_gazebo (Gazebo Classic) is replaced
by explorer_description's explorer_gazebo.launch.py, and turtlebot3_navigation2's
burger.yaml by config/nav2_params.yaml.

Deliberately does NOT reuse a navigation2.launch.py-style wrapper: those include
nav2_bringup's bringup_launch.py with its default slam:=False, which starts map_server
(serving a static map.yaml) and amcl. That fights with a live-mapping SLAM source.

SLAM Toolbox is started here, not through nav2_bringup's slam:=True. That path activates
SLAM Toolbox from a launch event handler, which races under CPU load: in one of six test
runs the node stayed unconfigured-inactive, no map -> odom transform ever appeared and
Nav2 aborted its bringup. Here Nav2's lifecycle manager configures and activates it (and
the map saver) through service calls instead. nav2_bringup gets use_localization:=False
so it starts neither its own SLAM Toolbox nor map_server/amcl - a second SLAM Toolbox
would race this one to publish /map and the map -> odom transform. Both read the same
params file, which is why nav2_params.yaml has a slam_toolbox section.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml

PKG_SHARE = get_package_share_directory('explorer_exploration')
NAV2_PARAMS = os.path.join(PKG_SHARE, 'config', 'nav2_params.yaml')


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')

    # The BT file must be an absolute path: point it at this package's install.
    params = RewrittenYaml(
        source_file=LaunchConfiguration('params_file'),
        param_rewrites={'default_nav_to_pose_bt_xml': os.path.join(
            PKG_SHARE, 'behavior_trees', 'explore_nav_to_pose.xml')},
        convert_types=True)

    sim_launch = os.path.join(
        get_package_share_directory('explorer_description'), 'launch',
        'explorer_gazebo.launch.py')
    nav2_launch = os.path.join(
        get_package_share_directory('nav2_bringup'), 'launch', 'bringup_launch.py')
    explore_launch = os.path.join(PKG_SHARE, 'launch', 'explore.launch.py')
    rviz_config = os.path.join(
        get_package_share_directory('nav2_bringup'), 'rviz', 'nav2_default_view.rviz')

    return LaunchDescription([
        DeclareLaunchArgument('sim', default_value='true',
                              description='true = Gazebo; false = the real robot (explorer_bringup)'),
        DeclareLaunchArgument('use_sim_time', default_value=LaunchConfiguration('sim')),
        DeclareLaunchArgument('world', default_value='cave.sdf',
                              description='Gazebo world (see explorer_description)'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('gui', default_value='true', description='Gazebo window'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('params_file', default_value=NAV2_PARAMS,
                              description='Nav2 + SLAM Toolbox parameters'),
        DeclareLaunchArgument('scoring_mode', default_value='tad',
                              description="'tad' or 'nearest' (baseline)"),
        DeclareLaunchArgument('selection_mode', default_value='dfs',
                              description="'dfs' (finish the branch first) or 'global' (original)"),

        # Robot, world, bridge, wheel+IMU EKF. cmd_vel is bridged as TwistStamped, which is
        # what nav2_params.yaml makes Nav2 publish (enable_stamped_cmd_vel).
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(sim_launch),
            launch_arguments={
                'world': LaunchConfiguration('world'),
                'x': LaunchConfiguration('x'),
                'y': LaunchConfiguration('y'),
                'yaw': LaunchConfiguration('yaw'),
                'gui': LaunchConfiguration('gui'),
                'cmd_vel_stamped': 'true',
            }.items(),
            condition=IfCondition(LaunchConfiguration('sim')),
        ),
        # Real robot: drivers, LiDAR, robot_state_publisher, EKF - same topics as the sim
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                get_package_share_directory('explorer_bringup'), 'launch', 'robot.launch.py')),
            condition=UnlessCondition(LaunchConfiguration('sim')),
        ),

        Node(
            package='slam_toolbox',
            executable='sync_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[params,
                        {'use_sim_time': use_sim_time, 'use_lifecycle_manager': True}],
        ),
        Node(
            package='nav2_map_server',
            executable='map_saver_server',
            name='map_saver',
            output='screen',
            parameters=[params, {'use_sim_time': use_sim_time}],
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_slam',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time, 'autostart': True,
                         'node_names': ['slam_toolbox', 'map_saver']}],
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav2_launch),
            launch_arguments={
                'slam': 'False',
                'use_localization': 'False',
                # Separate processes, not one component container: in discovery-server
                # mode the launch's load_node service call can miss the container and
                # silently leave Nav2 empty (no /navigate_to_pose server, no /cmd_vel).
                'use_composition': 'False',
                'map': '',
                'use_sim_time': use_sim_time,
                'params_file': params,
            }.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(explore_launch),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'scoring_mode': LaunchConfiguration('scoring_mode'),
                'selection_mode': LaunchConfiguration('selection_mode'),
            }.items(),
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(LaunchConfiguration('rviz')),
            output='screen',
        ),
    ])
