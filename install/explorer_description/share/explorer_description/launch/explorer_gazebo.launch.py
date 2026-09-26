"""
Launch the explorer robot in Gazebo Harmonic (ROS 2 Jazzy).

Run (after `colcon build` and `source install/setup.bash`):
    ros2 launch explorer_description explorer_gazebo.launch.py
    ros2 launch explorer_description explorer_gazebo.launch.py rviz:=true
    ros2 launch explorer_description explorer_gazebo.launch.py world:=/path/to/world.sdf
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

PKG_SHARE = get_package_share_directory("explorer_description")
XACRO_FILE = os.path.join(PKG_SHARE, "urdf", "explorer.urdf.xacro")
RVIZ_FILE = os.path.join(PKG_SHARE, "rviz", "explorer.rviz")


def generate_launch_description():
    world = LaunchConfiguration("world")
    rviz = LaunchConfiguration("rviz")

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
            "gz_args": ["-r ", world],
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
        arguments=["-topic", "robot_description", "-name", "explorer", "-z", "0.02"],
        output="screen",
    )

    # 4. Translate Gazebo topics <-> ROS 2 topics
    #    [  = Gazebo -> ROS      ]  = ROS -> Gazebo
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
            "/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
            "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model",
            "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
        ],
        parameters=[{"use_sim_time": True}],
        output="screen",
    )

    # 5. Optional RViz
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
                                  description="Gazebo world file"),
            DeclareLaunchArgument("rviz", default_value="false",
                                  description="Also open RViz"),
            gazebo,
            robot_state_publisher,
            spawn,
            bridge,
            rviz_node,
        ]
    )
