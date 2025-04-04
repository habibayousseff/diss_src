#!/usr/bin/env python3

# """
# unified_llm_nav.py
# One single node that:
#  - Provides a text-based interface to an LLM (OpenAI GPT).
#  - Moves the UR end effector to named cup goals in a MoveIt environment.

# To run interactively in a separate console, do:
#   ros2 run move_program unified_llm_nav.py

# Or if you want to have it launched automatically with your Gazebo + MoveIt,
# add it as a Node(...) in your combined.launch.py. 
# But be aware that interactive input might be messy if logs stream to the same console.
# """

# import os
# import sys
# import rclpy
# from rclpy.node import Node
# from rclpy.action import ActionClient

# import openai

# # MoveIt / geometry message imports
# from geometry_msgs.msg import Pose
# from shape_msgs.msg import SolidPrimitive
# from moveit_msgs.msg import (
#     MotionPlanRequest,
#     Constraints,
#     PositionConstraint,
#     OrientationConstraint,
#     PlanningOptions
# )
# from moveit_msgs.action import MoveGroup, ExecuteTrajectory

# # print(openai.__version__)

# # openai.api_key = "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"

# # Hard-coded dictionary of known object poses
# OBJECT_GOALS = {
#     "RedCup": {
#         "position": [1.01, 1.295022, 1.27],
#         "orientation": [0.720, 0.694, -0.029, -0.013]
#     },
#     "GreenCup": {
#         "position": [1.148940, 1.295022, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041]
#     },
#     "BlueCup": {
#         "position": [1.29, 1.27, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041]
#     },
#     "YellowCup": {
#         "position": [0.963062, 1.461358, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041]
#     },
#     "PurpleCup": {
#         "position": [1.168, 1.466, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041]
#     },
# }


# class LLMAndNavNode(Node):
#     def __init__(self):
#         super().__init__('llm_and_nav_node')

#         # Set your OpenAI API key here or via an environment variable:
#         openai.api_key = os.getenv("OPENAI_API_KEY", "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")

#         self.get_logger().info("LLM + Navigation Node started. Type commands in console...")

#         # Timer to poll for user input every 5 seconds
#         self.poll_timer = self.create_timer(5.0, self.poll_user)
#         self.busy = False

#         # We'll also keep an action client around for MoveGroup
#         self._move_client = ActionClient(self, MoveGroup, '/move_action')
#         self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')

#     def poll_user(self):
#         """Called periodically to ask the user for text input in the same console."""
#         if self.busy:
#             return
#         self.busy = True

#         user_text = input("\nType a command (e.g. 'Go to red cup'): ")
#         if not user_text.strip():
#             self.busy = False
#             return

#         # Step 1: Query GPT or GPT-4
#         response = self.query_llm(user_text)

#         # Step 2: Look for color in the LLM's text
#         self.get_logger().info(f"LLM says: {response}")
#         color = self.extract_color_from_response(response)

#         # If found a color, do a move
#         if color:
#             self.get_logger().info(f"Detected color: {color}. Moving now.")
#             self.move_to_named_goal(color)
#         else:
#             self.get_logger().info("No recognized color found in LLM response.")

#         self.busy = False

#     def query_llm(self, prompt_text):
#         """Minimal call to GPT-4 or GPT-3.5 via openai API"""
#         try:
#             resp = openai.chat.completions.create(
#                 model="gpt-3.5-turbo",  # or "gpt-3.5-turbo"
#                 messages=[
#                     {"role": "system", 
#                      "content": "You are a helpful robotics assistant. We have cups named RedCup, GreenCup, BlueCup, YellowCup, PurpleCup. If user wants to go to a cup, mention the color in your suggestion."},
#                     {"role": "user", "content": prompt_text},
#                 ],
#                 temperature=0.0,
#             )
#             return resp.choices[0].message.content
#         except Exception as e:
#             self.get_logger().error(f"OpenAI API error: {str(e)}")
#             return "Error: could not query LLM"

#     def extract_color_from_response(self, response_text):
#         """Naive check for color keywords in LLM response."""
#         lower = response_text.lower()
#         for color in ["red", "green", "blue", "yellow", "purple"]:
#             if color in lower:
#                 # Return the dictionary key: RedCup, GreenCup, etc.
#                 # We'll do a simple capital approach:
#                 return color.capitalize() + "Cup"
#         return None

#     def move_to_named_goal(self, goal_name: str):
#         """Send a MoveGroup action request to plan to the named goal (dictionary above)."""
#         if goal_name not in OBJECT_GOALS:
#             self.get_logger().error(f"No known goal for {goal_name}")
#             return

#         # Wait for servers
#         self.get_logger().info("Waiting for /move_action server...")
#         self._move_client.wait_for_server()
#         self.get_logger().info("Waiting for /execute_trajectory server...")
#         self._exec_client.wait_for_server()

#         # Build the MoveGroup request
#         pos = OBJECT_GOALS[goal_name]["position"]
#         ori = OBJECT_GOALS[goal_name]["orientation"]

#         goal_msg = MoveGroup.Goal()
#         request = MotionPlanRequest()
#         request.group_name = "ur_manipulator"
#         request.allowed_planning_time = 5.0
#         request.max_velocity_scaling_factor = 0.7
#         request.max_acceleration_scaling_factor = 0.7

#         constraints = Constraints()

#         # PositionConstraint
#         pc = PositionConstraint()
#         pc.header.frame_id = "world"
#         pc.link_name = "tool0"
#         pc.weight = 1.0

#         sphere = SolidPrimitive()
#         sphere.type = SolidPrimitive.SPHERE
#         sphere.dimensions = [0.008]  # small bounding region
#         sphere_pose = Pose()
#         sphere_pose.position.x = pos[0]
#         sphere_pose.position.y = pos[1]
#         sphere_pose.position.z = pos[2]
#         sphere_pose.orientation.w = 1.0
#         pc.constraint_region.primitives.append(sphere)
#         pc.constraint_region.primitive_poses.append(sphere_pose)

#         # OrientationConstraint
#         oc = OrientationConstraint()
#         oc.header.frame_id = "world"
#         oc.link_name = "tool0"
#         oc.orientation.x = ori[0]
#         oc.orientation.y = ori[1]
#         oc.orientation.z = ori[2]
#         oc.orientation.w = ori[3]
#         oc.absolute_x_axis_tolerance = 0.1
#         oc.absolute_y_axis_tolerance = 0.1
#         oc.absolute_z_axis_tolerance = 0.1
#         oc.weight = 1.0

#         constraints.position_constraints.append(pc)
#         constraints.orientation_constraints.append(oc)
#         request.goal_constraints.append(constraints)

#         # Minimal planning options
#         planning_options = PlanningOptions()
#         planning_options.planning_scene_diff.is_diff = True
#         planning_options.planning_scene_diff.robot_state.is_diff = True

#         goal_msg.request = request
#         goal_msg.planning_options = planning_options

#         self.get_logger().info(f"Sending MoveIt goal for: {goal_name}")
#         future = self._move_client.send_goal_async(goal_msg, feedback_callback=self.feedback_cb)
#         future.add_done_callback(self.goal_response_cb)

#     def feedback_cb(self, feedback_msg):
#         self.get_logger().info(f"Feedback: {feedback_msg.feedback}")

#     def goal_response_cb(self, future):
#         goal_handle = future.result()
#         if not goal_handle.accepted:
#             self.get_logger().error("MoveGroup goal was rejected.")
#             return

#         self.get_logger().info("Goal accepted; waiting for result...")
#         result_future = goal_handle.get_result_async()
#         result_future.add_done_callback(self.result_cb)

#     def result_cb(self, future):
#         result = future.result().result
#         if result.error_code.val == 1:
#             self.get_logger().info("Motion planning + execution succeeded!")
#         else:
#             self.get_logger().error(f"Motion failed with error code: {result.error_code.val}")


# def main(args=None):
#     rclpy.init(args=args)
#     node = LLMAndNavNode()
#     rclpy.spin(node)
#     node.destroy_node()
#     rclpy.shutdown()


# if __name__ == "__main__":
#     main()
    
    
    
    
    
    
    
    



























# """
# unified_llm_nav.py
# One single node that:
#  - Provides a text-based interface to an LLM (OpenAI GPT).
#  - Moves the UR end effector to named cup goals in a MoveIt environment.
#  - Includes pick/place functionality.
# """

# import os
# import sys
# import rclpy
# from rclpy.node import Node
# from rclpy.action import ActionClient
# from std_srvs.srv import SetBool
# import openai

# # MoveIt / geometry message imports
# from geometry_msgs.msg import Pose
# from shape_msgs.msg import SolidPrimitive
# from moveit_msgs.msg import (
#     MotionPlanRequest,
#     Constraints,
#     PositionConstraint,
#     OrientationConstraint,
#     PlanningOptions
# )
# from moveit_msgs.action import MoveGroup, ExecuteTrajectory

# # Hard-coded dictionary of known object poses
# OBJECT_GOALS = {
#     "RedCup": {
#         "position": [1.01, 1.295022, 1.27],
#         "orientation": [0.720, 0.694, -0.029, -0.013],
#         "place_position": [1.01, 0.8, 1.27]
#     },
#     "GreenCup": {
#         "position": [1.148940, 1.295022, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "place_position": [1.148940, 0.8, 1.27]
#     },
#     "BlueCup": {
#         "position": [1.29, 1.27, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "place_position": [1.29, 0.8, 1.27]
#     },
#     "YellowCup": {
#         "position": [0.963062, 1.461358, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "place_position": [0.963062, 0.8, 1.27]
#     },
#     "PurpleCup": {
#         "position": [1.168, 1.466, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "place_position": [1.168, 0.8, 1.27]
#     },
# }

# class LLMAndNavNode(Node):
#     def __init__(self):
#         super().__init__('llm_and_nav_node')

#         # Set your OpenAI API key
#         openai.api_key = os.getenv("OPENAI_API_KEY", "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")

#         # Pick service client
#         self.pick_client = self.create_client(SetBool, 'pick_up')
#         self.current_object = None  # Track held object

#         self.get_logger().info("LLM + Navigation Node started. Type commands in console...")

#         # Timer to poll for user input every 5 seconds
#         self.poll_timer = self.create_timer(5.0, self.poll_user)
#         self.busy = False

#         # Action clients for MoveIt
#         self._move_client = ActionClient(self, MoveGroup, '/move_action')
#         self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')

#     def poll_user(self):
#         """Called periodically to ask the user for text input."""
#         if self.busy:
#             return
#         self.busy = True

#         user_text = input("\nType a command (e.g. 'Go to red cup' or 'Pick up red cup'): ")
#         if not user_text.strip():
#             self.busy = False
#             return

#         # Query LLM
#         response = self.query_llm(user_text)
#         self.get_logger().info(f"LLM says: {response}")
        
#         # Process response
#         if "pick up" in response.lower() or "grab" in response.lower():
#             color = self.extract_color_from_response(response)
#             if color:
#                 self.execute_pick_sequence(color)
#         elif "place" in response.lower() or "put down" in response.lower():
#             self.execute_place_sequence()
#         else:
#             color = self.extract_color_from_response(response)
#             if color:
#                 self.move_to_named_goal(color)

#         self.busy = False

#     def execute_pick_sequence(self, color):
#         """Full pick sequence: move to object, pick, lift"""
#         self.current_object = color
#         self.move_to_named_goal(color)
#         self.call_pick_service(True)
#         self.lift_object()

#     def execute_place_sequence(self):
#         """Full place sequence: move to place position, release"""
#         if not self.current_object:
#             self.get_logger().warn("No object currently held")
#             return
            
#         place_pos = OBJECT_GOALS[self.current_object]["place_position"]
#         goal = {
#             "position": place_pos,
#             "orientation": OBJECT_GOALS[self.current_object]["orientation"]
#         }
#         self.move_to_named_goal(goal)
#         self.call_pick_service(False)
#         self.current_object = None

#     def call_pick_service(self, pick: bool):
#         """Call the pick/place service"""
#         req = SetBool.Request()
#         req.data = pick
#         future = self.pick_client.call_async(req)
#         future.add_done_callback(
#             lambda future: self.get_logger().info(
#                 f"{'Pick' if pick else 'Place'} service {'succeeded' if future.result().success else 'failed'}"
#             )
#         )

#     def lift_object(self):
#         """Lift the object after picking"""
#         if not self.current_object:
#             return
            
#         current_pos = OBJECT_GOALS[self.current_object]["position"]
#         lift_pos = [current_pos[0], current_pos[1], current_pos[2] + 0.2]  # 20cm higher
#         goal = {
#             "position": lift_pos,
#             "orientation": OBJECT_GOALS[self.current_object]["orientation"]
#         }
#         self.move_to_named_goal(goal)

#     def query_llm(self, prompt_text):
#         """Query GPT-3.5 via OpenAI API"""
#         try:
#             resp = openai.chat.completions.create(
#                 model="gpt-3.5-turbo",
#                 messages=[
#                     {"role": "system", 
#                      "content": "You are a helpful robotics assistant. We have cups named RedCup, GreenCup, BlueCup, YellowCup, PurpleCup. If user wants to go to a cup, mention the color in your suggestion."},
#                     {"role": "user", "content": prompt_text},
#                 ],
#                 temperature=0.0,
#             )
#             return resp.choices[0].message.content
#         except Exception as e:
#             self.get_logger().error(f"OpenAI API error: {str(e)}")
#             return "Error: could not query LLM"

#     def extract_color_from_response(self, response_text):
#         """Check for color keywords in LLM response."""
#         lower = response_text.lower()
#         for color in ["red", "green", "blue", "yellow", "purple"]:
#             if color in lower:
#                 return color.capitalize() + "Cup"
#         return None

#     def move_to_named_goal(self, goal):
#         """Send a MoveGroup action request to plan to the named goal"""
#         if isinstance(goal, str):
#             if goal not in OBJECT_GOALS:
#                 self.get_logger().error(f"No known goal for {goal}")
#                 return
#             goal_data = OBJECT_GOALS[goal]
#         else:
#             goal_data = goal

#         # Wait for servers
#         self._move_client.wait_for_server()
#         self._exec_client.wait_for_server()

#         # Build the MoveGroup request
#         pos = goal_data["position"]
#         ori = goal_data["orientation"]

#         goal_msg = MoveGroup.Goal()
#         request = MotionPlanRequest()
#         request.group_name = "ur_manipulator"
#         request.allowed_planning_time = 5.0
#         request.max_velocity_scaling_factor = 0.7
#         request.max_acceleration_scaling_factor = 0.7

#         constraints = Constraints()

#         # PositionConstraint
#         pc = PositionConstraint()
#         pc.header.frame_id = "world"
#         pc.link_name = "tool0"
#         pc.weight = 1.0

#         sphere = SolidPrimitive()
#         sphere.type = SolidPrimitive.SPHERE
#         sphere.dimensions = [0.008]
#         sphere_pose = Pose()
#         sphere_pose.position.x = pos[0]
#         sphere_pose.position.y = pos[1]
#         sphere_pose.position.z = pos[2]
#         sphere_pose.orientation.w = 1.0
#         pc.constraint_region.primitives.append(sphere)
#         pc.constraint_region.primitive_poses.append(sphere_pose)

#         # OrientationConstraint
#         oc = OrientationConstraint()
#         oc.header.frame_id = "world"
#         oc.link_name = "tool0"
#         oc.orientation.x = ori[0]
#         oc.orientation.y = ori[1]
#         oc.orientation.z = ori[2]
#         oc.orientation.w = ori[3]
#         oc.absolute_x_axis_tolerance = 0.1
#         oc.absolute_y_axis_tolerance = 0.1
#         oc.absolute_z_axis_tolerance = 0.1
#         oc.weight = 1.0

#         constraints.position_constraints.append(pc)
#         constraints.orientation_constraints.append(oc)
#         request.goal_constraints.append(constraints)

#         planning_options = PlanningOptions()
#         planning_options.planning_scene_diff.is_diff = True
#         planning_options.planning_scene_diff.robot_state.is_diff = True

#         goal_msg.request = request
#         goal_msg.planning_options = planning_options

#         self.get_logger().info(f"Sending MoveIt goal")
#         future = self._move_client.send_goal_async(goal_msg, feedback_callback=self.feedback_cb)
#         future.add_done_callback(self.goal_response_cb)

#     def feedback_cb(self, feedback_msg):
#         self.get_logger().info(f"Feedback: {feedback_msg.feedback}")

#     def goal_response_cb(self, future):
#         goal_handle = future.result()
#         if not goal_handle.accepted:
#             self.get_logger().error("MoveGroup goal was rejected.")
#             return

#         self.get_logger().info("Goal accepted; waiting for result...")
#         result_future = goal_handle.get_result_async()
#         result_future.add_done_callback(self.result_cb)

#     def result_cb(self, future):
#         result = future.result().result
#         if result.error_code.val == 1:
#             self.get_logger().info("Motion planning + execution succeeded!")
#         else:
#             self.get_logger().error(f"Motion failed with error code: {result.error_code.val}")

# def main(args=None):
#     rclpy.init(args=args)
#     node = LLMAndNavNode()
#     rclpy.spin(node)
#     node.destroy_node()
#     rclpy.shutdown()

# if __name__ == "__main__":
#     main()



















































# """
# Complete Unified LLM Navigation with Working Motion Planning and TF2 Attachment
# """

# import os
# import rclpy
# from rclpy.node import Node
# from rclpy.action import ActionClient
# from std_srvs.srv import SetBool
# from tf2_ros import TransformBroadcaster
# from geometry_msgs.msg import TransformStamped, Pose
# from shape_msgs.msg import SolidPrimitive
# from moveit_msgs.msg import (
#     MotionPlanRequest,
#     Constraints,
#     PositionConstraint,
#     OrientationConstraint,
#     PlanningOptions
# )
# from moveit_msgs.action import MoveGroup, ExecuteTrajectory
# import openai

# # Object Configuration
# OBJECT_GOALS = {
#     "RedCup": {
#         "position": [1.01, 1.295022, 1.27],
#         "orientation": [0.720, 0.694, -0.029, -0.013],
#         "place_position": [1.01, 0.8, 1.27],
#         "tf_frame": "red_plastic_cup"
#     },
#     "GreenCup": {
#         "position": [1.148940, 1.295022, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "place_position": [1.148940, 0.8, 1.27],
#         "tf_frame": "green_plastic_cup"
#     },
#     "BlueCup": {
#         "position": [1.29, 1.27, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "place_position": [1.29, 0.8, 1.27],
#         "tf_frame": "blue_plastic_cup"
#     },
#     "YellowCup": {
#         "position": [0.963062, 1.461358, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "place_position": [0.963062, 0.8, 1.27],
#         "tf_frame": "yellow_plastic_cup"
#     },
#     "PurpleCup": {
#         "position": [1.168, 1.466, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "place_position": [1.168, 0.8, 1.27],
#         "tf_frame": "purple_plastic_cup"
#     },
# }

# class ObjectTFManager:
#     """Handles object attachment using TF2 transforms"""
#     def __init__(self, node):
#         self.node = node
#         self.tf_broadcaster = TransformBroadcaster(node)
#         self.attached_object = None
#         self.timer = node.create_timer(0.1, self.update_tf)  # 10Hz update

#     def attach(self, object_frame):
#         """Attach object to end effector"""
#         self.attached_object = object_frame
#         self.node.get_logger().info(f"Attached {object_frame} to end effector")

#     def detach(self):
#         """Detach current object"""
#         if self.attached_object:
#             self.node.get_logger().info(f"Detached {self.attached_object}")
#         self.attached_object = None

#     def update_tf(self):
#         """Publish transform for attached object"""
#         if self.attached_object:
#             t = TransformStamped()
#             t.header.stamp = self.node.get_clock().now().to_msg()
#             t.header.frame_id = "tool0"  # End effector frame
#             t.child_frame_id = self.attached_object
#             t.transform.translation.z = 0.05  # 5cm above gripper
#             t.transform.rotation.w = 1.0  # Neutral orientation
#             self.tf_broadcaster.sendTransform(t)

# class LLMAndNavNode(Node):
#     def __init__(self):
#         super().__init__('llm_and_nav_node')
        
#         # Initialize components
#         self.object_tf = ObjectTFManager(self)
#         self.current_object = None
#         openai.api_key = os.getenv("OPENAI_API_KEY", "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")

#         # Service clients
#         self.pick_client = self.create_client(SetBool, '/pick_up')

#         # Action clients
#         self._move_client = ActionClient(self, MoveGroup, '/move_action')
#         self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')

#         # User interface
#         self.poll_timer = self.create_timer(5.0, self.poll_user)
#         self.busy = False

#     def poll_user(self):
#         """Handle user input"""
#         if self.busy: return
#         self.busy = True
        
#         try:
#             user_text = input("\nCommand (e.g., 'Pick up red cup'): ").strip()
#             if not user_text:
#                 self.busy = False
#                 return

#             # Query LLM
#             response = self.query_llm(user_text)
#             self.get_logger().info(f"LLM says: {response}")
            
#             # Process command
#             if "pick" in response.lower() or "grab" in response.lower():
#                 color = self.extract_color_from_response(response)
#                 if color: 
#                     self.execute_pick_sequence(color)
#             elif "place" in response.lower() or "put down" in response.lower():
#                 self.execute_place_sequence()
#             else:
#                 color = self.extract_color_from_response(response)
#                 if color: 
#                     self.move_to_named_goal(color)
#         except Exception as e:
#             self.get_logger().error(f"Error processing command: {str(e)}")
#         finally:
#             self.busy = False

#     def execute_pick_sequence(self, obj_name):
#         """Full pick sequence: move -> pick -> attach -> lift"""
#         self.current_object = obj_name
#         self.move_to_named_goal(obj_name)
#         self.call_pick_service(True)
#         self.object_tf.attach(OBJECT_GOALS[obj_name]["tf_frame"])
#         self.lift_object()

#     def execute_place_sequence(self):
#         """Full place sequence: move -> detach -> place"""
#         if not self.current_object:
#             self.get_logger().warn("No object held!")
#             return
        
#         goal = {
#             "position": OBJECT_GOALS[self.current_object]["place_position"],
#             "orientation": OBJECT_GOALS[self.current_object]["orientation"]
#         }
#         self.move_to_named_goal(goal)
#         self.object_tf.detach()
#         self.call_pick_service(False)
#         self.current_object = None

#     def call_pick_service(self, pick: bool):
#         """Call the physical gripper service"""
#         req = SetBool.Request()
#         req.data = pick
#         future = self.pick_client.call_async(req)
#         future.add_done_callback(
#             lambda future: self.get_logger().info(
#                 f"{'Pick' if pick else 'Place'} service {'succeeded' if future.result().success else 'failed'}"
#             )
#         )

#     def lift_object(self):
#         """Lift the object after picking"""
#         if not self.current_object: return
            
#         current_pos = OBJECT_GOALS[self.current_object]["position"]
#         lift_pos = [current_pos[0], current_pos[1], current_pos[2] + 0.2]
#         goal = {
#             "position": lift_pos,
#             "orientation": OBJECT_GOALS[self.current_object]["orientation"]
#         }
#         self.move_to_named_goal(goal)

#     def move_to_named_goal(self, goal):
#         """Move to predefined goal (either string name or pose dict)"""
#         if isinstance(goal, str):
#             if goal not in OBJECT_GOALS:
#                 self.get_logger().error(f"Unknown goal: {goal}")
#                 return
#             goal_data = OBJECT_GOALS[goal]
#         else:
#             goal_data = goal

#         # Wait for servers
#         self._move_client.wait_for_server()
#         self._exec_client.wait_for_server()

#         # Build the MoveGroup request
#         pos = goal_data["position"]
#         ori = goal_data["orientation"]

#         goal_msg = MoveGroup.Goal()
#         request = MotionPlanRequest()
#         request.group_name = "ur_manipulator"
#         request.allowed_planning_time = 5.0
#         request.max_velocity_scaling_factor = 0.7
#         request.max_acceleration_scaling_factor = 0.7

#         constraints = Constraints()

#         # PositionConstraint
#         pc = PositionConstraint()
#         pc.header.frame_id = "world"
#         pc.link_name = "tool0"
#         pc.weight = 1.0

#         sphere = SolidPrimitive()
#         sphere.type = SolidPrimitive.SPHERE
#         sphere.dimensions = [0.008]
#         sphere_pose = Pose()
#         sphere_pose.position.x = pos[0]
#         sphere_pose.position.y = pos[1]
#         sphere_pose.position.z = pos[2]
#         sphere_pose.orientation.w = 1.0
#         pc.constraint_region.primitives.append(sphere)
#         pc.constraint_region.primitive_poses.append(sphere_pose)

#         # OrientationConstraint
#         oc = OrientationConstraint()
#         oc.header.frame_id = "world"
#         oc.link_name = "tool0"
#         oc.orientation.x = ori[0]
#         oc.orientation.y = ori[1]
#         oc.orientation.z = ori[2]
#         oc.orientation.w = ori[3]
#         oc.absolute_x_axis_tolerance = 0.1
#         oc.absolute_y_axis_tolerance = 0.1
#         oc.absolute_z_axis_tolerance = 0.1
#         oc.weight = 1.0

#         constraints.position_constraints.append(pc)
#         constraints.orientation_constraints.append(oc)
#         request.goal_constraints.append(constraints)

#         planning_options = PlanningOptions()
#         planning_options.planning_scene_diff.is_diff = True
#         planning_options.planning_scene_diff.robot_state.is_diff = True

#         goal_msg.request = request
#         goal_msg.planning_options = planning_options

#         self.get_logger().info(f"Sending MoveIt goal")
#         future = self._move_client.send_goal_async(goal_msg)
#         future.add_done_callback(self.goal_response_cb)

#     def goal_response_cb(self, future):
#         goal_handle = future.result()
#         if not goal_handle.accepted:
#             self.get_logger().error("MoveGroup goal was rejected.")
#             return

#         self.get_logger().info("Goal accepted; waiting for result...")
#         result_future = goal_handle.get_result_async()
#         result_future.add_done_callback(self.result_cb)

#     def result_cb(self, future):
#         result = future.result().result
#         if result.error_code.val == 1:
#             self.get_logger().info("Motion planning + execution succeeded!")
#         else:
#             self.get_logger().error(f"Motion failed with error code: {result.error_code.val}")

#     def query_llm(self, prompt_text):
#         """Query OpenAI GPT-3.5"""
#         try:
#             resp = openai.chat.completions.create(
#                 model="gpt-3.5-turbo",
#                 messages=[{
#                     "role": "system",
#                     "content": "You control a robot arm. Available cups: RedCup, GreenCup, BlueCup, YellowCup, PurpleCup."
#                 }, {
#                     "role": "user",
#                     "content": prompt_text
#                 }],
#                 temperature=0.0
#             )
#             return resp.choices[0].message.content
#         except Exception as e:
#             self.get_logger().error(f"LLM Error: {str(e)}")
#             return "Error: could not query LLM"

#     def extract_color_from_response(self, response_text):
#         """Extract color from LLM response"""
#         lower = response_text.lower()
#         for color in ["red", "green", "blue", "yellow", "purple"]:
#             if color in lower:
#                 return color.capitalize() + "Cup"
#         return None

# def main(args=None):
#     rclpy.init(args=args)
#     node = LLMAndNavNode()
#     try:
#         rclpy.spin(node)
#     except KeyboardInterrupt:
#         pass
#     finally:
#         node.destroy_node()
#         rclpy.shutdown()

# if __name__ == "__main__":
#     main()






















































# """
# Simplified Unified LLM Navigation (No Gripper Required)
# - Uses TF2 transforms for object attachment
# - No dependency on /pick_up service
# - Full motion planning
# """

# import os
# import rclpy
# from rclpy.node import Node
# from rclpy.action import ActionClient
# from tf2_ros import TransformBroadcaster
# from geometry_msgs.msg import TransformStamped, Pose
# from shape_msgs.msg import SolidPrimitive
# from moveit_msgs.msg import (
#     MotionPlanRequest,
#     Constraints,
#     PositionConstraint,
#     OrientationConstraint,
#     PlanningOptions
# )
# from moveit_msgs.action import MoveGroup, ExecuteTrajectory
# import openai

# # Object Configuration
# OBJECT_GOALS = {
#     "RedCup": {
#         "position": [1.01, 1.295022, 1.27],
#         "orientation": [0.720, 0.694, -0.029, -0.013],
#         "tf_frame": "red_plastic_cup"
#     },
#     "GreenCup": {
#         "position": [1.148940, 1.295022, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "tf_frame": "green_plastic_cup"
#     },
#     "BlueCup": {
#         "position": [1.29, 1.27, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "tf_frame": "blue_plastic_cup"
#     },
#     "YellowCup": {
#         "position": [0.963062, 1.461358, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "tf_frame": "yellow_plastic_cup"
#     },
#     "PurpleCup": {
#         "position": [1.168, 1.466, 1.27],
#         "orientation": [0.714, 0.699, -0.032, -0.041],
#         "tf_frame": "purple_plastic_cup"
#     },
# }

# class ObjectTFManager:
#     """Handles object attachment using TF2"""
#     def __init__(self, node):
#         self.node = node
#         self.tf_broadcaster = TransformBroadcaster(node)
#         self.attached_object = None
#         self.timer = node.create_timer(0.1, self.update_tf)  # 10Hz update
#         self.node.get_logger().info("TF Manager initialized")

#     def attach(self, object_frame):
#         """Attach object to end effector"""
#         self.attached_object = object_frame
#         self.node.get_logger().info(f"Attached {object_frame}")

#     def detach(self):
#         """Detach current object"""
#         self.attached_object = None
#         self.node.get_logger().info("Detached object")

#     def update_tf(self):
#         """Publish transform for attached object"""
#         if self.attached_object:
#             t = TransformStamped()
#             t.header.stamp = self.node.get_clock().now().to_msg()
#             t.header.frame_id = "wrist_3_link"  # End effector frame
#             t.child_frame_id = self.attached_object
#             t.transform.translation.z = 0.05  # 5cm above gripper
#             t.transform.rotation.w = 1.0  # Neutral orientation
#             self.tf_broadcaster.sendTransform(t)

# class LLMAndNavNode(Node):
#     def __init__(self):
#         super().__init__('llm_and_nav_node')
        
#         # Initialize components
#         self.object_tf = ObjectTFManager(self)
#         self.current_object = None
#         openai.api_key = os.getenv("OPENAI_API_KEY", "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")

#         # Action clients (no service client needed)
#         self._move_client = ActionClient(self, MoveGroup, '/move_action')
#         self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')

#         # User interface
#         self.poll_timer = self.create_timer(5.0, self.poll_user)
#         self.busy = False
#         self.get_logger().info("Node ready for commands")

#     def poll_user(self):
#         """Handle user input"""
#         if self.busy:
#             return
#         self.busy = True
        
#         try:
#             user_text = input("\nCommand (e.g., 'Pick up red cup'): ").strip()
#             if not user_text:
#                 return

#             response = self.query_llm(user_text)
#             self.get_logger().info(f"LLM says: {response}")
            
#             # Process command
#             if "pick" in response.lower():
#                 color = self.extract_color(response)
#                 if color:
#                     self.execute_pick_sequence(color)
#             elif "place" in response.lower():
#                 self.execute_place_sequence()
#             else:
#                 color = self.extract_color(response)
#                 if color:
#                     self.move_to_named_goal(color)
#         except Exception as e:
#             self.get_logger().error(f"Command error: {str(e)}")
#         finally:
#             self.busy = False

#     def execute_pick_sequence(self, obj_name):
#         """Pick sequence without gripper service"""
#         self.current_object = obj_name
#         self.move_to_named_goal(obj_name)
#         self.object_tf.attach(OBJECT_GOALS[obj_name]["tf_frame"])  # Virtual attach
#         self.lift_object()

#     def execute_place_sequence(self):
#         """Place sequence without gripper service"""
#         if not self.current_object:
#             self.get_logger().warn("No object held!")
#             return
        
#         goal = {
#             "position": OBJECT_GOALS[self.current_object]["place_position"],
#             "orientation": OBJECT_GOALS[self.current_object]["orientation"]
#         }
#         self.move_to_named_goal(goal)
#         self.object_tf.detach()  # Virtual detach
#         self.current_object = None
    
#     def call_pick_service(self, pick: bool):
#         """Call the physical gripper service"""
#         req = SetBool.Request()
#         req.data = pick
#         future = self.pick_client.call_async(req)
#         future.add_done_callback(
#             lambda future: self.get_logger().info(
#                 f"{'Pick' if pick else 'Place'} service {'succeeded' if future.result().success else 'failed'}"
#             )
#         )

#     def lift_object(self):
#         """Lift the object after picking"""
#         if not self.current_object: return
            
#         current_pos = OBJECT_GOALS[self.current_object]["position"]
#         lift_pos = [current_pos[0], current_pos[1], current_pos[2] + 0.2]
#         goal = {
#             "position": lift_pos,
#             "orientation": OBJECT_GOALS[self.current_object]["orientation"]
#         }
#         self.move_to_named_goal(goal)

#     def move_to_named_goal(self, goal):
#         """Move to predefined goal (either string name or pose dict)"""
#         if isinstance(goal, str):
#             if goal not in OBJECT_GOALS:
#                 self.get_logger().error(f"Unknown goal: {goal}")
#                 return
#             goal_data = OBJECT_GOALS[goal]
#         else:
#             goal_data = goal

#         # Wait for servers
#         self._move_client.wait_for_server()
#         self._exec_client.wait_for_server()

#         # Build the MoveGroup request
#         pos = goal_data["position"]
#         ori = goal_data["orientation"]

#         goal_msg = MoveGroup.Goal()
#         request = MotionPlanRequest()
#         request.group_name = "ur_manipulator"
#         request.allowed_planning_time = 5.0
#         request.max_velocity_scaling_factor = 0.7
#         request.max_acceleration_scaling_factor = 0.7

#         constraints = Constraints()

#         # PositionConstraint
#         pc = PositionConstraint()
#         pc.header.frame_id = "world"
#         pc.link_name = "wrist_3_link"
#         pc.weight = 1.0

#         sphere = SolidPrimitive()
#         sphere.type = SolidPrimitive.SPHERE
#         sphere.dimensions = [0.008]
#         sphere_pose = Pose()
#         sphere_pose.position.x = pos[0]
#         sphere_pose.position.y = pos[1]
#         sphere_pose.position.z = pos[2]
#         sphere_pose.orientation.w = 1.0
#         pc.constraint_region.primitives.append(sphere)
#         pc.constraint_region.primitive_poses.append(sphere_pose)

#         # OrientationConstraint
#         oc = OrientationConstraint()
#         oc.header.frame_id = "world"
#         oc.link_name = "wrist_3_link"
#         oc.orientation.x = ori[0]
#         oc.orientation.y = ori[1]
#         oc.orientation.z = ori[2]
#         oc.orientation.w = ori[3]
#         oc.absolute_x_axis_tolerance = 0.1
#         oc.absolute_y_axis_tolerance = 0.1
#         oc.absolute_z_axis_tolerance = 0.1
#         oc.weight = 1.0

#         constraints.position_constraints.append(pc)
#         constraints.orientation_constraints.append(oc)
#         request.goal_constraints.append(constraints)

#         planning_options = PlanningOptions()
#         planning_options.planning_scene_diff.is_diff = True
#         planning_options.planning_scene_diff.robot_state.is_diff = True

#         goal_msg.request = request
#         goal_msg.planning_options = planning_options

#         self.get_logger().info(f"Sending MoveIt goal")
#         future = self._move_client.send_goal_async(goal_msg)
#         future.add_done_callback(self.goal_response_cb)

#     def goal_response_cb(self, future):
#         goal_handle = future.result()
#         if not goal_handle.accepted:
#             self.get_logger().error("MoveGroup goal was rejected.")
#             return

#         self.get_logger().info("Goal accepted; waiting for result...")
#         result_future = goal_handle.get_result_async()
#         result_future.add_done_callback(self.result_cb)

#     def result_cb(self, future):
#         result = future.result().result
#         if result.error_code.val == 1:
#             self.get_logger().info("Motion planning + execution succeeded!")
#         else:
#             self.get_logger().error(f"Motion failed with error code: {result.error_code.val}")

#     def query_llm(self, prompt_text):
#         """Query OpenAI GPT-3.5"""
#         try:
#             resp = openai.chat.completions.create(
#                 model="gpt-3.5-turbo",
#                 messages=[{
#                     "role": "system",
#                     "content": "You control a robot arm. Available cups: RedCup, GreenCup, BlueCup, YellowCup, PurpleCup."
#                 }, {
#                     "role": "user",
#                     "content": prompt_text
#                 }],
#                 temperature=0.0
#             )
#             return resp.choices[0].message.content
#         except Exception as e:
#             self.get_logger().error(f"LLM Error: {str(e)}")
#             return "Error: could not query LLM"

#     def extract_color(self, response_text):
#         """Extract color from LLM response"""
#         lower = response_text.lower()
#         for color in ["red", "green", "blue", "yellow", "purple"]:
#             if color in lower:
#                 return color.capitalize() + "Cup"
#         return None

# def main(args=None):
#     rclpy.init(args=args)
#     node = LLMAndNavNode()
#     try:
#         rclpy.spin(node)
#     except KeyboardInterrupt:
#         pass
#     finally:
#         node.destroy_node()
#         rclpy.shutdown()

# if __name__ == "__main__":
#     main()

























































import os
import rclpy
import time
from rclpy.node import Node
from rclpy.action import ActionClient
from tf2_ros import TransformBroadcaster, Buffer, TransformListener
from geometry_msgs.msg import TransformStamped, Pose
from shape_msgs.msg import SolidPrimitive
from moveit_msgs.msg import (
    MotionPlanRequest, Constraints, PositionConstraint,
    OrientationConstraint, PlanningOptions, CollisionObject, AttachedCollisionObject
)
from moveit_msgs.action import MoveGroup, ExecuteTrajectory
from gazebo_msgs.srv import LinkRequest
from std_msgs.msg import Header
import openai


# Object Configuration
OBJECT_GOALS = {
    "RedCup": {
        "position": [1.01, 1.295022, 1.27],
        "orientation": [0.720, 0.694, -0.029, -0.013],
        "tf_frame": "red_plastic_cup",
        "dimensions": [0.1, 0.04]  # Height, radius
    },
    "GreenCup": {
        "position": [1.148940, 1.295022, 1.27],
        "orientation": [0.714, 0.699, -0.032, -0.041],
        "tf_frame": "green_plastic_cup",
        "dimensions": [0.1, 0.04]
    },
    "BlueCup": {
        "position": [1.29, 1.27, 1.27],
        "orientation": [0.714, 0.699, -0.032, -0.041],
        "tf_frame": "blue_plastic_cup",
        "dimensions": [0.1, 0.04]
    },
    "YellowCup": {
        "position": [0.963062, 1.461358, 1.27],
        "orientation": [0.714, 0.699, -0.032, -0.041],
        "tf_frame": "yellow_plastic_cup",
        "dimensions": [0.1, 0.04]
    },
    "PurpleCup": {
        "position": [1.168, 1.466, 1.27],
        "orientation": [0.714, 0.699, -0.032, -0.041],
        "tf_frame": "purple_plastic_cup",
        "dimensions": [0.1, 0.04]
    },
}

class LLMAndNavNode(Node):
    def __init__(self):
        super().__init__('llm_and_nav_node')
        
        # TF and MoveIt
        self.object_tf = ObjectTFManager(self)
        self.current_object = None
        
        # Action clients
        self._move_client = ActionClient(self, MoveGroup, '/move_action')
        self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        
        # Gazebo attachment service
        self.gazebo_attach_client = self.create_client(
            LinkRequest, '/link_attacher_node/attach'
        )
        self.gazebo_detach_client = self.create_client(
            LinkRequest, '/link_attacher_node/detach'
        )
        
        # Planning scene publisher
        self._planning_scene_pub = self.create_publisher(
            AttachedCollisionObject,
            '/attached_collision_object',
            10
        )
        
        # User interface
        self.poll_timer = self.create_timer(5.0, self.poll_user)
        self.get_logger().info("Node ready for commands")

    def execute_pick_sequence(self, obj_name):
        """Full pick sequence with Gazebo physics"""
        self.current_object = obj_name
        self.move_to_named_goal(obj_name)
        time.sleep(2.0)  # Wait for arm to reach
        
        # Virtual attachment (TF + MoveIt)
        self.object_tf.attach(OBJECT_GOALS[obj_name]["tf_frame"])
        self.attach_to_planning_scene(obj_name)
        
        # Physical attachment (Gazebo)
        self.attach_gazebo_object(OBJECT_GOALS[obj_name]["gazebo_model"])
        
        self.lift_object()

    def attach_gazebo_object(self, model_name):
        """Physically attach object in Gazebo"""
        req = LinkRequest.Request()
        req.model_name_1 = "ur5e"  # Your robot model name
        req.link_name_1 = "tool0"
        req.model_name_2 = model_name
        req.link_name_2 = "link"  # From cup SDF
        future = self.gazebo_attach_client.call_async(req)
        future.add_done_callback(
            lambda _: self.get_logger().info(f"Gazebo attached: {model_name}")
        )

    def execute_place_sequence(self):
        """Place sequence with Gazebo detach"""
        if not self.current_object:
            self.get_logger().warn("No object held!")
            return
            
        # Physical detach (Gazebo)
        req = LinkRequest.Request()
        req.model_name_1 = "ur5e"
        req.link_name_1 = "tool0"
        req.model_name_2 = OBJECT_GOALS[self.current_object]["gazebo_model"]
        req.link_name_2 = "link"
        self.gazebo_detach_client.call_async(req)
        
        # Virtual detach (TF + MoveIt)
        self.object_tf.detach()
        self.detach_from_planning_scene()
        self.current_object = None
    
    def move_to_named_goal(self, goal):
        """Move to predefined goal (either string name or pose dict)"""
        if isinstance(goal, str):
            if goal not in OBJECT_GOALS:
                self.get_logger().error(f"Unknown goal: {goal}")
                return
            goal_data = OBJECT_GOALS[goal]
        else:
            goal_data = goal

        # Wait for servers
        self._move_client.wait_for_server()
        self._exec_client.wait_for_server()

        # Build the MoveGroup request
        pos = goal_data["position"]
        ori = goal_data["orientation"]

        goal_msg = MoveGroup.Goal()
        request = MotionPlanRequest()
        request.group_name = "ur_manipulator"
        request.allowed_planning_time = 5.0
        request.max_velocity_scaling_factor = 0.7
        request.max_acceleration_scaling_factor = 0.7

        constraints = Constraints()

        # PositionConstraint
        pc = PositionConstraint()
        pc.header.frame_id = "world"
        pc.link_name = "wrist_3_link"
        pc.weight = 1.0

        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [0.008]
        sphere_pose = Pose()
        sphere_pose.position.x = pos[0]
        sphere_pose.position.y = pos[1]
        sphere_pose.position.z = pos[2]
        sphere_pose.orientation.w = 1.0
        pc.constraint_region.primitives.append(sphere)
        pc.constraint_region.primitive_poses.append(sphere_pose)

        # OrientationConstraint
        oc = OrientationConstraint()
        oc.header.frame_id = "world"
        oc.link_name = "wrist_3_link"
        oc.orientation.x = ori[0]
        oc.orientation.y = ori[1]
        oc.orientation.z = ori[2]
        oc.orientation.w = ori[3]
        oc.absolute_x_axis_tolerance = 0.1
        oc.absolute_y_axis_tolerance = 0.1
        oc.absolute_z_axis_tolerance = 0.1
        oc.weight = 1.0

        constraints.position_constraints.append(pc)
        constraints.orientation_constraints.append(oc)
        request.goal_constraints.append(constraints)

        planning_options = PlanningOptions()
        planning_options.planning_scene_diff.is_diff = True
        planning_options.planning_scene_diff.robot_state.is_diff = True

        goal_msg.request = request
        goal_msg.planning_options = planning_options

        self.get_logger().info(f"Sending MoveIt goal")
        future = self._move_client.send_goal_async(goal_msg)
        future.add_done_callback(self.goal_response_cb)

    def goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("MoveGroup goal was rejected.")
            return

        self.get_logger().info("Goal accepted; waiting for result...")
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_cb)

    def result_cb(self, future):
        result = future.result().result
        if result.error_code.val == 1:
            self.get_logger().info("Motion planning + execution succeeded!")
        else:
            self.get_logger().error(f"Motion failed with error code: {result.error_code.val}")

    def query_llm(self, prompt_text):
        """Query OpenAI GPT-3.5"""
        try:
            resp = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "You control a robot arm. Available cups: RedCup, GreenCup, BlueCup, YellowCup, PurpleCup."
                }, {
                    "role": "user",
                    "content": prompt_text
                }],
                temperature=0.0
            )
            return resp.choices[0].message.content
        except Exception as e:
            self.get_logger().error(f"LLM Error: {str(e)}")
            return "Error: could not query LLM"

    def extract_color(self, response_text):
        """Extract color from LLM response"""
        lower = response_text.lower()
        for color in ["red", "green", "blue", "yellow", "purple"]:
            if color in lower:
                return color.capitalize() + "Cup"
        return None

def main(args=None):
    rclpy.init(args=args)
    node = LLMAndNavNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()