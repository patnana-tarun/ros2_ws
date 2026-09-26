"""
Launch the explorer robot in Gazebo Harmonic (ROS 2 Jazzy).

Run (after `colcon build` and `source install/setup.bash`):
    ros2 launch explorer_description explorer_gazebo.launch.py
    ros2 launch explorer_description explorer_gazebo.launch.py rviz:=true
    ros2 launch explorer_description explorer_gazebo.launch.py world:=cave.sdf
    ros2 launch explorer_description explorer_gazebo.launch.py world:=cave_open.sdf
    ros2 launch explorer_description explorer_gazebo.launch.py world:=/path/to/world.sdf x:=1 y:=2 yaw:=1.57
    ros2 launch explorer_description explorer_gazebo.launch.py cmd_vel_stamped:=false
    ros2 launch explorer_description explorer_gazebo.launch.py gui:=false   # headless

Odometry: Gazebo publishes wheel odometry (/wheel/odom) and the IMU (/imu); a
robot_localization EKF fuses them into /odom and the odom -> base_footprint transform,
the same way the real robot will.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument,
                            IncludeLaunchDescription)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

PKG_SHARE = get_package_share_directory("explorer_description")
XACRO_FILE = os.path.join(PKG_SHARE, "urdf", "explorer.urdf.xacro")
RVIZ_FILE = os.path.join(PKG_SHARE, "rviz", "explorer.rviz")
EKF_FILE = os.path.join(PKG_SHARE, "config", "ekf.yaml")
# Lets Gazebo find the cave worlds by name (world:=cave.sdf) and their model:// meshes
RESOURCE_PATHS = [os.path.join(PKG_SHARE, "worlds"), os.path.join(PKG_SHARE, "models")]


def generate_launch_description():
    world = LaunchConfiguration("world")
    rviz = LaunchConfiguration("rviz")
    cmd_vel_stamped = LaunchConfiguration("cmd_vel_stamped")
    headless = PythonExpression(["'' if '", LaunchConfiguration("gui"),
                                 "'.lower() == 'true' else '-s --headless-rendering '"])

    # Jazzy's turtlebot3 teleop publishes TwistStamped; Nav2 and teleop_twist_keyboard
    # publish Twist. A bridge only connects to one ROS type, so pick it here.
    cmd_vel_bridge = PythonExpression([
        "'/cmd_vel@geometry_msgs/msg/TwistStamped]gz.msgs.Twist' if '",
        cmd_vel_stamped,
        "'.lower() == 'true' else '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist'",
    ])

    robot_description = ParameterValue(
        Command(["xacro ", XACRO_FILE]), value_type=str
    )

    # 1. Gazebo (-r = start playing immediately)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("ros_gz_sim"),
                "launch",
                "gz_sim.launch.py",
            )
        ),
        launch_arguments={
            "gz_args": ["-r ", headless, world],
            "on_exit_shutdown": "true",
        }.items(),
    )

    # 2. Publishes robot_description + TF for every part
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description, "use_sim_time": True}],
        output="screen",
    )

    # 3. Put the robot into the Gazebo world
    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-topic", "robot_description", "-name", "explorer",
                   "-x", LaunchConfiguration("x"), "-y", LaunchConfiguration("y"),
                   "-z", "0.02", "-Y", LaunchConfiguration("yaw")],
        output="screen",
    )

    # 4. Translate Gazebo topics <-> ROS 2 topics
    #    [  = Gazebo -> ROS      ]  = ROS -> Gazebo
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            cmd_vel_bridge,
            "/wheel/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/imu@sensor_msgs/msg/Imu[gz.msgs.IMU",
            "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model",
            "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
        ],
        parameters=[{"use_sim_time": True}],
        output="screen",
    )

    # 5. Wheel odometry + IMU -> /odom and TF odom -> base_footprint
    ekf = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node",
        parameters=[EKF_FILE, {"use_sim_time": True}],
        remappings=[("odometry/filtered", "odom")],
        output="screen",
    )

    # 6. Optional RViz
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", RVIZ_FILE],
        parameters=[{"use_sim_time": True}],
        condition=IfCondition(rviz),
        output="screen",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("world", default_value="empty.sdf",
                                  description="Gazebo world: empty.sdf, cave.sdf, cave_open.sdf or a path"),
            DeclareLaunchArgument("rviz", default_value="false",
                                  description="Also open RViz"),
            DeclareLaunchArgument("gui", default_value="true",
                                  description="Open the Gazebo window (false = headless server)"),
            DeclareLaunchArgument("cmd_vel_stamped", default_value="true",
                                  description="Bridge /cmd_vel as TwistStamped (true) or Twist (false)"),
            DeclareLaunchArgument("x", default_value="0.0", description="Spawn x (m)"),
            DeclareLaunchArgument("y", default_value="0.0", description="Spawn y (m)"),
            DeclareLaunchArgument("yaw", default_value="0.0", description="Spawn yaw (rad)"),
            *[AppendEnvironmentVariable("GZ_SIM_RESOURCE_PATH", p) for p in RESOURCE_PATHS],
            gazebo,
            robot_state_publisher,
            spawn,
            bridge,
            ekf,
            rviz_node,
        ]
    )
