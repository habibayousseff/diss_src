import os
import yaml
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, ExecuteProcess, OpaqueFunction, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,    # Runs shell commands (e.g., processing xacro files)
    FindExecutable, # Finds executables in the ROS 2 environment
    LaunchConfiguration,    # Stores values from launch arguments
    PathJoinSubstitution,   # Ensures correct file path formatting
    IfElseSubstitution, # Allows selecting between two values based on a condition
)
from launch_ros.actions import Node # Defines ROS 2 nodes to be launched
from launch_ros.substitutions import FindPackageShare   # Finds package locations
from ament_index_python.packages import get_package_share_directory

def launch_setup(context, *args, **kwargs):
    # Load parameters from launch arguments
    ur_type = LaunchConfiguration("ur_type").perform(context)
    safety_limits = LaunchConfiguration("safety_limits").perform(context)
    safety_pos_margin = LaunchConfiguration("safety_pos_margin").perform(context)
    safety_k_position = LaunchConfiguration("safety_k_position").perform(context)
    
    controllers_file = LaunchConfiguration("controllers_file").perform(context)
    tf_prefix = LaunchConfiguration("tf_prefix").perform(context)
    activate_joint_controller = LaunchConfiguration("activate_joint_controller").perform(context)
    initial_joint_controller = LaunchConfiguration("initial_joint_controller").perform(context)
    description_file = LaunchConfiguration("description_file").perform(context)
    launch_rviz = LaunchConfiguration("launch_rviz").perform(context)
    rviz_config_file = LaunchConfiguration("rviz_config_file").perform(context)
    gazebo_gui = LaunchConfiguration("gazebo_gui").perform(context)
    world_file = LaunchConfiguration("world_file").perform(context)

    # Expand the URDF using xacro
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            description_file,
            " ",
            "safety_limits:=", safety_limits,
            " ",
            "safety_pos_margin:=", safety_pos_margin,
            " ",
            "safety_k_position:=", safety_k_position,
            " ",
            "name:=", "ur",
            " ",
            "ur_type:=", ur_type,
            " ",
            "tf_prefix:=", tf_prefix,
            " ",
            "simulation_controllers:=", controllers_file,
        ]
    )
    
    # Create the dictionary for robot_description
    robot_description = {"robot_description": robot_description_content}

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[{"use_sim_time": True}, robot_description],
    )


    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
        condition=IfCondition(LaunchConfiguration("launch_rviz")),
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    delay_rviz_after_joint_state_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[rviz_node],
        ),
        condition=IfCondition(LaunchConfiguration("launch_rviz")),
    )

    initial_joint_controller_spawner_started = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[initial_joint_controller, "-c", "/controller_manager"],
        condition=IfCondition(LaunchConfiguration("activate_joint_controller")),
    )
    initial_joint_controller_spawner_stopped = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[initial_joint_controller, "-c", "/controller_manager", "--stopped"],
        condition=UnlessCondition(LaunchConfiguration("activate_joint_controller")),
    )

    gz_spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-string",
            robot_description_content,
            "-name",
            "ur",
            "-allow_renaming",
            "true",
        ],
    )

    gz_launch_description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("ros_gz_sim"), "/launch/gz_sim.launch.py"]
        ),
        launch_arguments={
            "gz_args": IfElseSubstitution(
                LaunchConfiguration("gazebo_gui"),
                if_value=[" -r -v 4 ", world_file],
                else_value=[" -s -r -v 4 ", world_file],
            )
        }.items(),
    )

    gz_sim_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )
    
    nodes_to_start = [
        robot_state_publisher_node,
        joint_state_broadcaster_spawner,
        delay_rviz_after_joint_state_broadcaster_spawner,
        initial_joint_controller_spawner_stopped,
        initial_joint_controller_spawner_started,
        gz_spawn_entity,
        gz_launch_description,
        gz_sim_bridge,
    ]
    
    return nodes_to_start


def generate_launch_description():
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            "ur_type",
            description="Type/series of used UR robot.",
            default_value="ur5",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "safety_limits",
            default_value="true",
            description="Enables the safety limits controller if true.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "safety_pos_margin",
            default_value="0.15",
            description="The margin to lower and upper limits in the safety controller.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "safety_k_position",
            default_value="20",
            description="k-position factor in the safety controller.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "controllers_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("ur_simulation_gz"), "config", "ur_controllers.yaml"]
            ),
            description="Absolute path to YAML file with the controllers configuration.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "tf_prefix",
            default_value='""',
            description="Prefix of the joint names (useful for multi-robot setups).",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "activate_joint_controller",
            default_value="true",
            description="Enable headless mode for robot control.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "initial_joint_controller",
            default_value="scaled_joint_trajectory_controller",
            description="Robot controller to start.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "description_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("ur_simulation_gz"), "urdf", "ur_gz.urdf.xacro"]
            ),
            description="URDF/XACRO description file (absolute path) with the robot.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument("launch_rviz", default_value="false", description="Launch RViz?")
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "rviz_config_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("ur_description"), "rviz", "view_robot.rviz"]
            ),
            description="RViz config file (absolute path) to use when launching RViz.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "gazebo_gui", default_value="true", description="Start Gazebo with GUI?"
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "world_file",
            default_value=PathJoinSubstitution(
                [
                    "/home/habibahassan/project/src/Universal_Robots_ROS2_GZ_Simulation/ur_simulation_gz/worlds",
                    "trial.sdf"
                ]
            ),
            description="Gazebo world file containing a custom world.",
        )
    )

    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])


if __name__ == "__main__":
    generate_launch_description()
