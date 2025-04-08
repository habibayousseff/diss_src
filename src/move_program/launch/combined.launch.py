"""
Combined Launch File:
This file merges the logic of both your simulation launch (or_sim.launch.py)
and your MoveIt2 launch (ur_moveit.launch.py) into one unified file.
It sets up the robot in Gazebo, configures MoveIt2 (with its controllers,
move_group, and RViz), and launches all necessary simulation and planning nodes.
All nodes share the same parameter context so that parameters (e.g. robot_description)
are passed consistently.
"""

import os
import yaml
import time
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, ExecuteProcess, OpaqueFunction, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
    IfElseSubstitution,
)
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription
from moveit_configs_utils import MoveItConfigsBuilder

def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    try:
        with open(absolute_file_path) as file:
            return yaml.safe_load(file)
    except OSError:
        return None

def launch_setup(context, *args, **kwargs):
    ur_type = LaunchConfiguration("ur_type").perform(context)
    safety_limits = LaunchConfiguration("safety_limits").perform(context)
    safety_pos_margin = LaunchConfiguration("safety_pos_margin").perform(context)
    safety_k_position = LaunchConfiguration("safety_k_position").perform(context)
    controllers_file = LaunchConfiguration("controllers_file").perform(context)
    tf_prefix = LaunchConfiguration("tf_prefix").perform(context)
    description_file = LaunchConfiguration("description_file").perform(context)

    activate_joint_controller = LaunchConfiguration("activate_joint_controller").perform(context)
    initial_joint_controller = LaunchConfiguration("initial_joint_controller").perform(context)
    launch_rviz_sim = LaunchConfiguration("launch_rviz_sim").perform(context)
    rviz_config_file_sim = LaunchConfiguration("rviz_config_file_sim").perform(context)
    gazebo_gui = LaunchConfiguration("gazebo_gui").perform(context)
    world_file = LaunchConfiguration("world_file").perform(context)

    warehouse_sqlite_path = LaunchConfiguration("warehouse_sqlite_path").perform(context)
    launch_servo = LaunchConfiguration("launch_servo").perform(context)
    use_sim_time = LaunchConfiguration("use_sim_time").perform(context)
    publish_robot_description_semantic = LaunchConfiguration("publish_robot_description_semantic").perform(context)

    launch_rviz_moveit = LaunchConfiguration("launch_rviz_moveit").perform(context)
    rviz_config_file_moveit = LaunchConfiguration("rviz_config_file_moveit").perform(context)

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
    robot_description = {"robot_description": robot_description_content}
    expanded_urdf = robot_description_content.perform(context)

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[{"use_sim_time": True}, robot_description],
    )

    gz_launch_description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")
        ),
        launch_arguments={
            "gz_args": IfElseSubstitution(
                LaunchConfiguration("gazebo_gui"),
                if_value=[" -r -v 4 ", world_file],
                else_value=[" -s -r -v 4 ", world_file],
            )
        }.items(),
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

    gz_sim_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )
    
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )
    
    # ros2_controllers_path = os.path.join(
    #     get_package_share_directory("ur_robot_driver"), "config", "ur_controllers.yaml"
    # )
    
    # ros2_control_node = Node(
    #     package="controller_manager",
    #     executable="ros2_control_node",
    #     parameters=[ros2_controllers_path],
    #     output="both",
    # )
    
    spawn_controllers = []
    for ctrl in ["joint_state_broadcaster", "scaled_joint_trajectory_controller"]:
        spawn_controllers.append(
            ExecuteProcess(
                cmd=["ros2 run controller_manager spawner {}".format(ctrl)],
                shell=True,
                output="screen",
            )
        )
    
    # delay_ros2_control = RegisterEventHandler(
    #     OnProcessExit(
    #         target_action=robot_state_publisher_node,
    #         on_exit=[ros2_control_node],
    #     )
    # )
    
    initial_joint_controller_spawner_started = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[initial_joint_controller, "-c", "/controller_manager"],
        condition=IfCondition(LaunchConfiguration("activate_joint_controller")),
    )
    
    gripper_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["gripper_controller", "-c", "/controller_manager"],
        output="screen",
    )
    
    # delay_gripper_spawner = RegisterEventHandler(
    #     event_handler=OnProcessExit(
    #         target_action=ros2_control_node,  # Wait for the control node
    #         on_exit=[gripper_controller_spawner]
    #     )
    # )

    wait_robot_description = Node(
        package="ur_robot_driver",
        executable="wait_for_robot_description",
        output="screen",
    )

    robot_description_publisher_node = Node(
        package="move_program",
        executable="robot_description_publisher.py",
        parameters=[{"use_sim_time": True}, expanded_urdf],
        output="screen"
    )
    
    moveit_config = (
        MoveItConfigsBuilder(robot_name="ur", package_name="ur_moveit_config")
        .robot_description_semantic(Path("srdf") / "ur.srdf.xacro", {"name": ur_type})
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .planning_scene_monitor(
            publish_robot_description=True,
            publish_robot_description_semantic=True
        )
        .to_moveit_configs()
    )
    
    warehouse_ros_config = {
        "warehouse_plugin": "warehouse_ros_sqlite::DatabaseConnection",
        "warehouse_host": warehouse_sqlite_path,
    }
    
    move_group_capabilities = {"capabilities": "move_group/ExecuteTaskSolutionCapability"}

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            move_group_capabilities,
            warehouse_ros_config,
            {
                "use_sim_time": True,
                "publish_robot_description_semantic": publish_robot_description_semantic,
            },
        ],
    )

    rviz_moveit_node = Node(
        package="rviz2",
        condition=IfCondition(LaunchConfiguration("launch_rviz_moveit")),
        executable="rviz2",
        name="rviz2_moveit",
        output="log",
        arguments=["-d", rviz_config_file_moveit],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
            warehouse_ros_config,
            {"use_sim_time": True},
        ],
    )

    rviz_sim_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2_sim",
        output="log",
        arguments=["-d", rviz_config_file_sim],
        condition=IfCondition(LaunchConfiguration("launch_rviz_sim")),
    )

    delay_rviz_after_joint_state_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[rviz_sim_node],
        ),
        condition=IfCondition(LaunchConfiguration("launch_rviz_sim")),
    )
    
    servo_yaml = load_yaml("ur_moveit_config", "config/ur_servo.yaml")
    servo_params = {"moveit_servo": servo_yaml}
    servo_node = Node(
        package="moveit_servo",
        condition=IfCondition(LaunchConfiguration("launch_servo")),
        executable="servo_node",
        parameters=[moveit_config.to_dict(), servo_params],
        output="screen",
    )

    initial_joint_controller_spawner_stopped = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[initial_joint_controller, "-c", "/controller_manager", "--stopped"],
        condition=UnlessCondition(LaunchConfiguration("activate_joint_controller")),
    )

    delay_move_group_after_wait = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=wait_robot_description,
            on_exit=[move_group_node, rviz_moveit_node, servo_node],
        )
    )

    nodes_to_start = [
        robot_state_publisher_node,
        gz_launch_description,
        gz_spawn_entity,
        gz_sim_bridge,
        joint_state_broadcaster_spawner,
        wait_robot_description,
        robot_description_publisher_node,
        initial_joint_controller_spawner_stopped,
        initial_joint_controller_spawner_started,
        gripper_controller_spawner,
        delay_move_group_after_wait,
        delay_rviz_after_joint_state_broadcaster_spawner,
    ]
    nodes_to_start.extend(spawn_controllers)

    return nodes_to_start

def generate_launch_description():
    ld = LaunchDescription()

    ld.add_action(DeclareLaunchArgument("ur_type", default_value="ur5"))
    ld.add_action(DeclareLaunchArgument("safety_limits", default_value="true"))
    ld.add_action(DeclareLaunchArgument("safety_pos_margin", default_value="0.15"))
    ld.add_action(DeclareLaunchArgument("safety_k_position", default_value="20"))
    ld.add_action(DeclareLaunchArgument("controllers_file", default_value=os.path.join(
        get_package_share_directory("ur_robot_driver"), "config", "ur_controllers.yaml"
    )))
    ld.add_action(DeclareLaunchArgument("tf_prefix", default_value=""))
    ld.add_action(DeclareLaunchArgument("description_file", default_value=os.path.join(
        get_package_share_directory("ur_simulation_gz"), "urdf", "ur_gz.urdf.xacro"
    )))
    ld.add_action(DeclareLaunchArgument("activate_joint_controller", default_value="true"))
    ld.add_action(DeclareLaunchArgument("initial_joint_controller", default_value="scaled_joint_trajectory_controller"))
    ld.add_action(DeclareLaunchArgument("launch_rviz_sim", default_value="false"))
    ld.add_action(DeclareLaunchArgument("rviz_config_file_sim", default_value=os.path.join(
        get_package_share_directory("ur_description"), "rviz", "view_robot.rviz"
    )))
    ld.add_action(DeclareLaunchArgument("gazebo_gui", default_value="true"))
    ld.add_action(DeclareLaunchArgument("world_file", default_value="/home/habibahassan/project/src/move_program/world/OR_sim.sdf"))
    ld.add_action(DeclareLaunchArgument("warehouse_sqlite_path", default_value="~/.ros/warehouse_ros.sqlite"))
    ld.add_action(DeclareLaunchArgument("launch_servo", default_value="false"))
    ld.add_action(DeclareLaunchArgument("use_sim_time", default_value="true"))
    ld.add_action(DeclareLaunchArgument("publish_robot_description_semantic", default_value="true"))
    ld.add_action(DeclareLaunchArgument("launch_rviz_moveit", default_value="true"))
    ld.add_action(DeclareLaunchArgument("rviz_config_file_moveit", default_value=os.path.join(
        get_package_share_directory("ur_moveit_config"), "config", "moveit.rviz"
    )))

    ld.add_action(OpaqueFunction(function=launch_setup))

    collison_objects_node = Node(
        package="move_program",
        executable="collison_objects.py",
        output="screen",
    )
    ld.add_action(collison_objects_node)

    llm_node = Node(
        package="move_program",
        executable="llm_node.py",
        output="screen",
    )
    ld.add_action(llm_node)

    link_attacher_node = Node(
        package="move_program",
        executable="llm_node.py",
        output="screen",
    )
    ld.add_action(link_attacher_node)

    return ld

if __name__ == '__main__':
    time.sleep(20)
    generate_launch_description()
