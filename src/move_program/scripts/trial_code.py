#!/usr/bin/env python3
# import rclpy
# import os
# import yaml
# from rclpy.node import Node
# from rclpy.action import ActionClient

# from std_msgs.msg import String
# from sensor_msgs.msg import JointState
# from moveit_msgs.msg import PlanningScene
# from geometry_msgs.msg import PoseStamped
# from ament_index_python.packages import get_package_share_directory

# # MoveIt’s "move_group" action
# from moveit_msgs.action import MoveGroup
# from moveit_msgs.action import ExecuteTrajectory
# from moveit_msgs.msg import MotionPlanRequest, PlanningOptions

# # If you want to see the status from the /execute_trajectory action:
# from action_msgs.msg import GoalStatusArray  # for the action’s status messages

# def load_yaml(package_name, file_path):
#     package_path = get_package_share_directory(package_name)
#     absolute_file_path = os.path.join(package_path, file_path)
#     try:
#         with open(absolute_file_path) as file:
#             return yaml.safe_load(file)
#     except OSError:
#         return None

# servo_yaml = load_yaml("ur_moveit_config", "config/ur_servo.yaml")
# servo_params = {"moveit_servo": servo_yaml}

# class MoveGroupActionClient(Node):
#     def __init__(self):
#         super().__init__('move_group_action_client')

#         # 1) Create action client for the /move_action (move_group) server
#         self._move_action_client = ActionClient(self, MoveGroup, 'move_action')
#         self._execute_trajectory_client = ActionClient(self, ExecuteTrajectory, 'execute_trajectory')
#         # 2) Subscribe to /robot_description (optional)
#         self._robot_desc_sub = self.create_subscription(
#             String,
#             '/robot_description',
#             self._robot_description_callback,
#             10
#         )

#         # 3) Subscribe to planning scene (optional)
#         self._planning_scene_sub = self.create_subscription(
#             PlanningScene,
#             '/planning_scene',
#             self._planning_scene_callback,
#             10
#         )

#         # 4) Subscribe to joint_states (optional)
#         self._joint_states_sub = self.create_subscription(
#             JointState,
#             '/joint_states',
#             self._joint_states_callback,
#             10
#         )

#         # 5) Subscribe to robot_description_semantic (optional)
#         self._semantic_sub = self.create_subscription(
#             String,
#             '/robot_description_semantic',
#             self._semantic_callback,
#             10
#         )
        
#     def _robot_description_callback(self, msg: String):
#         self.get_logger().info("Received /robot_description snippet: %s" % msg.data[:80])

#     def _planning_scene_callback(self, msg: PlanningScene):
#         self.get_logger().info("Received /planning_scene update with %d collision objects"
#                                % len(msg.world.collision_objects))

#     def _joint_states_callback(self, msg: JointState):
#         self.get_logger().debug("Got /joint_states: %s" % msg.name)

#     def _semantic_callback(self, msg: String):
#         self.get_logger().info("Received /robot_description_semantic snippet: %s" % msg.data[:80])

#     def send_goal(self):
#         self.get_logger().info("Waiting for /move_action (move_group) server...")
#         self._move_action_client.wait_for_server()
#         self.get_logger().info("Waiting for /execute_trajectory_action (move_group) server...")
#         self._execute_trajectory_client.wait_for_server()

#         # Build the MoveGroup goal
#         goal_msg = MoveGroup.Goal()

#         # Minimal MotionPlanRequest
#         request = MotionPlanRequest()
#         request.group_name = "ur_manipulator"  # or your group name

#         # Example pose target (not yet converted to constraints!)
#         pose_goal = PoseStamped()
#         pose_goal.header.frame_id = "world"
#         pose_goal.pose.position.x = 1.061
#         pose_goal.pose.position.y = 0.542
#         pose_goal.pose.position.z = 2.101
#         pose_goal.pose.orientation.w = 1.0
#         # request.goal_constraints = convert_pose_to_constraints(pose_goal)

#         goal_msg.request = request

#         # Optionally specify planning options
#         planning_options = PlanningOptions()
#         planning_options.planning_scene_diff.is_diff = True
#         planning_options.planning_scene_diff.robot_state.is_diff = True
#         goal_msg.planning_options = planning_options

#         # Send the MoveGroup goal
#         send_goal_future = self._move_action_client.send_goal_async(
#             goal_msg, feedback_callback=self.feedback_callback
#         )
#         send_goal_future.add_done_callback(self.goal_response_callback)

#     def feedback_callback(self, feedback_msg):
#         self.get_logger().info(f"Feedback from move_group: {feedback_msg.feedback}")

#     def goal_response_callback(self, future):
#         goal_handle = future.result()
#         if not goal_handle.accepted:
#             self.get_logger().error("Goal rejected by move_group")
#             return
#         self.get_logger().info("Goal accepted; waiting for result...")
#         goal_handle.get_result_async().add_done_callback(self.get_result_callback)

#     def get_result_callback(self, future):
#         result = future.result().result
#         self.get_logger().info(f"Result: {result}")
#         rclpy.shutdown()

# def main(args=None):
#     rclpy.init(args=args)
#     node = MoveGroupActionClient()
#     node.send_goal()
#     rclpy.spin(node)

# if __name__ == '__main__':
#     main()

import rclpy
import os
import yaml
from rclpy.node import Node
from rclpy.action import ActionClient

from std_msgs.msg import String
from sensor_msgs.msg import JointState
from moveit_msgs.msg import PlanningScene
from geometry_msgs.msg import PoseStamped
from ament_index_python.packages import get_package_share_directory

# MoveIt’s "move_group" action
from moveit_msgs.action import MoveGroup
from moveit_msgs.action import ExecuteTrajectory
from moveit_msgs.msg import MotionPlanRequest, PlanningOptions

# For status messages (if needed)
from action_msgs.msg import GoalStatusArray

def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    try:
        with open(absolute_file_path) as file:
            return yaml.safe_load(file)
    except OSError:
        return None

servo_yaml = load_yaml("ur_moveit_config", "config/ur_servo.yaml")
servo_params = {"moveit_servo": servo_yaml}

class MoveGroupActionClient(Node):
    def __init__(self):
        super().__init__('move_group_action_client')

        # 1) Create action client for the /move_action (move_group) server
        self._move_action_client = ActionClient(self, MoveGroup, 'move_action')
        self._execute_trajectory_client = ActionClient(self, ExecuteTrajectory, 'execute_trajectory')

        # 2) Subscribe to /robot_description
        self._robot_desc_sub = self.create_subscription(
            String,
            '/robot_description',
            self._robot_description_callback,
            10
        )

        # 3) Subscribe to planning scene
        self._planning_scene_sub = self.create_subscription(
            PlanningScene,
            '/planning_scene',
            self._planning_scene_callback,
            10
        )

        # 4) Subscribe to joint_states
        self._joint_states_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self._joint_states_callback,
            10
        )

        # 5) Subscribe to robot_description_semantic
        self._semantic_sub = self.create_subscription(
            String,
            '/robot_description_semantic',
            self._semantic_callback,
            10
        )
        
    def _robot_description_callback(self, msg: String):
        # Print the full robot_description message content (or a longer snippet)
        self.get_logger().info("Full /robot_description: %s" % msg.data)
        
    def _planning_scene_callback(self, msg: PlanningScene):
        # Print some details about the planning scene
        collision_count = len(msg.world.collision_objects) if msg.world and msg.world.collision_objects else 0
        self.get_logger().info("Full /planning_scene: %s" % msg)
        self.get_logger().info("Number of collision objects: %d" % collision_count)
        
    def _joint_states_callback(self, msg: JointState):
        # Print the full joint states message
        self.get_logger().info("Full /joint_states: %s" % msg)
        
    def _semantic_callback(self, msg: String):
        # Print the full robot_description_semantic message content
        self.get_logger().info("Full /robot_description_semantic: %s" % msg.data)
        
    def send_goal(self):
        self.get_logger().info("Waiting for /move_action (move_group) server...")
        self._move_action_client.wait_for_server()
        self.get_logger().info("Waiting for /execute_trajectory (move_group) server...")
        self._execute_trajectory_client.wait_for_server()

        # Build the MoveGroup goal
        goal_msg = MoveGroup.Goal()

        # Minimal MotionPlanRequest
        request = MotionPlanRequest()
        request.group_name = "ur_manipulator"  # or your group name

        # Example pose target (not yet converted to constraints)
        pose_goal = PoseStamped()
        pose_goal.header.frame_id = "world"
        pose_goal.pose.position.x = 1.061
        pose_goal.pose.position.y = 0.542
        pose_goal.pose.position.z = 2.101
        pose_goal.pose.orientation.w = 1.0
        # request.goal_constraints = convert_pose_to_constraints(pose_goal)

        goal_msg.request = request

        # Specify planning options
        planning_options = PlanningOptions()
        planning_options.planning_scene_diff.is_diff = True
        planning_options.planning_scene_diff.robot_state.is_diff = True
        goal_msg.planning_options = planning_options

        # Send the MoveGroup goal
        send_goal_future = self._move_action_client.send_goal_async(
            goal_msg, feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)

    def feedback_callback(self, feedback_msg):
        self.get_logger().info(f"Feedback from move_group: {feedback_msg.feedback}")

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal rejected by move_group")
            return
        self.get_logger().info("Goal accepted; waiting for result...")
        goal_handle.get_result_async().add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result
        self.get_logger().info(f"Result: {result}")
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = MoveGroupActionClient()
    node.send_goal()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
