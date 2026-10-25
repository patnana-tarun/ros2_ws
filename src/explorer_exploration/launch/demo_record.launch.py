"""
Demo recording (user's request, 2026-10-24): a backup video of the explorer for the review panel,
in case the live demo fails.

    ros2 launch explorer_exploration demo_record.launch.py                  # sim + cameras + recording
    ros2 launch explorer_exploration demo_record.launch.py record:=false    # live demo, no recording
    ros2 launch explorer_exploration demo_record.launch.py box_x:=6.0 box_y:=6.0 glide_s:=0.0
    ros2 launch explorer_exploration demo_record.launch.py spawn:=random    # random safe start (new each run)
    ros2 launch explorer_exploration demo_record.launch.py x:=9.0 y:=-1.5 yaw:=1.57   # chosen start
    ros2 launch explorer_exploration demo_record.launch.py start_sim:=false # sim already running
                                                       # (started with rviz:=false; give its x/y/yaw too)
Ctrl-C stops everything; the video is in ~/demo_recordings/demo_<date>_<time>.mp4.

Starts:
  tunnel_reverse.launch.py  (current best navigation) with rviz:=false and the demo Gazebo layout
                            config/demo_gui.config (3D view only, no side panel)
  demo_chase_cam            Gazebo camera behind and above the robot, heading smoothed
  demo_view_box             TF view_anchor: still while the robot is inside the box, glides to the
                            robot when it leaves; the box is drawn on /demo/view_box
  rviz2                     rviz/demo_view.rviz: Nav2's default view centred on view_anchor,
                            docks hidden, right half of the screen
  demo_hud                  explored % and time, live, in RViz; drag it with the Interact tool
                            (key i), it stays there (saved); hud_x:= hud_y:= place it (m from
                            the view centre, x right, y up)
  demo_recorder             Gazebo | RViz side by side, one MP4

Spawn (spawn_point.py): spawn:=random picks a safe place (>= 0.6 m from rock) and heading, printed
at start (add seed:=N to repeat one); otherwise x/y/yaw (default 0, 0, 0) are used, and a point in
or too close to rock moves to the nearest safe place.

The cameras only follow the robot's pose, so manual driving works too: run
`ros2 run explorer_exploration manual_drive` in another terminal (exploration pauses while it runs).
Each piece also runs on its own, see the docstrings of demo_chase_cam / demo_view_box / demo_recorder.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, LogInfo,
                            OpaqueFunction, TimerAction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

from explorer_exploration.spawn_point import choose

PKG_SHARE = get_package_share_directory('explorer_exploration')


def sim_and_hud(context):
    v = lambda n: LaunchConfiguration(n).perform(context)
    seed = int(v('seed')) if v('seed') else None
    x, y, yaw, note = choose(v('spawn'), float(v('x')), float(v('y')), float(v('yaw')), v('world'), seed)
    xyz = {'x': f'{x:.2f}', 'y': f'{y:.2f}', 'yaw': f'{yaw:.2f}'}
    return [
        LogInfo(msg=f'demo_record: {note}  (repeat it: x:={x:.2f} y:={y:.2f} yaw:={yaw:.2f})'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(PKG_SHARE, 'launch', 'tunnel_reverse.launch.py')),
            launch_arguments={
                'world': v('world'),
                'rviz': 'false',
                'gui_config': os.path.join(PKG_SHARE, 'config', 'demo_gui.config'),
                **xyz,
            }.items(),
            condition=IfCondition(v('start_sim')),
        ),
        Node(
            package='explorer_exploration',
            executable='demo_hud',
            name='demo_hud',
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'spawn_x': x, 'spawn_y': y, 'spawn_yaw': yaw,
                'box_y': float(v('box_y')),
                **({'hud_x': float(v('hud_x')), 'hud_y': float(v('hud_y'))}
                   if v('hud_x') and v('hud_y') else {}),
                # the true-floor field fits cave.sdf only
                'field_file': '' if os.path.basename(v('world')) != 'cave.sdf' else
                              os.path.expanduser('~/ros2_ws/data/demo_runs_2026-10-19/field.npz'),
            }],
            condition=IfCondition(v('hud')),
        ),
    ]


def generate_launch_description():
    arg = LaunchConfiguration
    return LaunchDescription([
        DeclareLaunchArgument('start_sim', default_value='true',
                              description='false = use a sim that is already running'),
        DeclareLaunchArgument('world', default_value='cave.sdf'),
        DeclareLaunchArgument('spawn', default_value='manual',
                              description='random = random safe start; manual = x, y, yaw'),
        DeclareLaunchArgument('x', default_value='0.0', description='start x (m), spawn:=manual'),
        DeclareLaunchArgument('y', default_value='0.0', description='start y (m), spawn:=manual'),
        DeclareLaunchArgument('yaw', default_value='0.0', description='start heading (rad), spawn:=manual'),
        DeclareLaunchArgument('seed', default_value='', description='repeat a random spawn'),
        DeclareLaunchArgument('hud', default_value='true', description='explored % and time in RViz'),
        DeclareLaunchArgument('hud_x', default_value='', description='HUD x from the view centre (m); '
                              'empty = where it was last dragged'),
        DeclareLaunchArgument('hud_y', default_value='', description='HUD y from the view centre (m)'),
        DeclareLaunchArgument('record', default_value='true', description='record the MP4'),
        DeclareLaunchArgument('out_dir', default_value=os.path.expanduser('~/demo_recordings')),
        DeclareLaunchArgument('layout', default_value='side', description='side | screen'),
        DeclareLaunchArgument('chase', default_value='true', description='Gazebo chase camera'),
        DeclareLaunchArgument('distance', default_value='1.2', description='chase camera behind (m)'),
        DeclareLaunchArgument('height', default_value='0.6', description='chase camera above (m)'),
        DeclareLaunchArgument('yaw_tau', default_value='1.5',
                              description='chase heading smoothing (s), 0 = strictly behind'),
        DeclareLaunchArgument('box_x', default_value='4.0', description='view box size x (m)'),
        DeclareLaunchArgument('box_y', default_value='4.0', description='view box size y (m)'),
        DeclareLaunchArgument('glide_s', default_value='1.0', description='recentre time (s), 0 = snap'),
        DeclareLaunchArgument('show_box', default_value='true', description='draw the box in RViz'),

        OpaqueFunction(function=sim_and_hud),
        Node(
            package='rviz2',
            executable='rviz2',
            name='demo_rviz',
            arguments=['-d', os.path.join(PKG_SHARE, 'rviz', 'demo_view.rviz')],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
        Node(
            package='explorer_exploration',
            executable='demo_view_box',
            name='demo_view_box',
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'box_x': ParameterValue(arg('box_x'), value_type=float),
                'box_y': ParameterValue(arg('box_y'), value_type=float),
                'glide_s': ParameterValue(arg('glide_s'), value_type=float),
                'show_box': ParameterValue(arg('show_box'), value_type=bool),
            }],
        ),
        ExecuteProcess(
            cmd=['ros2', 'run', 'explorer_exploration', 'demo_chase_cam',
                 '--distance', arg('distance'), '--height', arg('height'), '--yaw-tau', arg('yaw_tau')],
            output='screen',
            condition=IfCondition(arg('chase')),
        ),
        # give Gazebo and RViz time to open their windows before tiling them
        TimerAction(period=5.0, actions=[ExecuteProcess(
            cmd=['ros2', 'run', 'explorer_exploration', 'demo_recorder',
                 '--out-dir', arg('out_dir'), '--layout', arg('layout')],
            output='screen',
            sigterm_timeout='15',
            condition=IfCondition(arg('record')),
        )]),
    ])
