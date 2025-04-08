#!/usr/bin/env python3
# import os
# import sys
# import time

# import rclpy
# from rclpy.node import Node
# from rclpy.action import ActionClient

# from geometry_msgs.msg import Pose
# from shape_msgs.msg import SolidPrimitive
# from control_msgs.action import GripperCommand
# from moveit_msgs.action import MoveGroup, ExecuteTrajectory
# from moveit_msgs.msg import (
#     MotionPlanRequest,
#     Constraints,
#     PositionConstraint,
#     OrientationConstraint,
#     PlanningOptions
# )
# import openai

# ###############################################################################
# #                            SHARED DICTIONARIES
# ###############################################################################
# OBJECT_GOALS = {
#     "RedCup": {
#         "position": [0.9226, 1.2018, 1.368],
#         "orientation": [0.739, 0.673, 0.014, -0.023],
#     },
#     "GreenCup": {
#         "position": [1.184, 1.281, 1.384],
#         "orientation": [0.739, 0.673, 0.014, -0.023],
#     },
#     "BlueCup": {
#         "position": [1.46, 1.203, 1.368],
#         "orientation": [0.739, 0.673, 0.014, -0.023],
#     },
#     "YellowCup": {
#         "position": [0.99, 1.427, 1.368],
#         "orientation": [0.739, 0.673, 0.014, -0.023],
#     },
#     "PurpleCup": {
#         "position": [1.385, 1.393, 1.368],
#         "orientation": [0.739, 0.673, 0.014, -0.023],
#     },
# }

# PLACE_GOAL = {
#     "TrialPlaceGoal": {
#         "position": [1.154, 0.249, 1.293],
#         "orientation": [-0.041, 0.999, -0.002, -0.006]
#     },
#     "TestConfig": {
#         "position": [1.154, 0.288, 1.604],
#         "orientation": [-0.040, 0.996, 0.076, -0.009]
#     },
#     "HOME": {
#         "position": [1.061, 0.542, 2.101],
#         "orientation": [0.000, -0.707, 0.707, 0.000]
#     },
#     "A": {
#         "position": [1.42, -0.042, 1.35],
#         "orientation": [-0.041, 0.999, -0.002, -0.006]
#     },
#     "B": {
#         "position": [1.113, -0.037, 1.35],
#         "orientation": [-0.041, 0.999, -0.002, -0.006]
#     },
#     "C": {
#         "position": [0.839, -0.0514, 1.35],
#         "orientation": [-0.041, 0.999, -0.002, -0.006]
#     },
#     "AA": {
#         "position": [1.43, 0.215, 1.35],
#         "orientation": [-0.041, 0.999, -0.002, -0.006]
#     },
#     "BB": {
#         "position": [1.131, 0.22, 1.35],
#         "orientation": [-0.041, 0.999, -0.002, -0.006]
#     },
#     "CC": {
#         "position": [0.83, 0.21, 1.35],
#         "orientation": [-0.041, 0.999, -0.002, -0.006]
#     },
# }

# ###############################################################################
# #                          GRIPPER CONSTANTS
# ###############################################################################
# GRIPPER_OPEN = 0.004
# GRIPPER_MIDDLE = 0.06
# GRIPPER_CLOSE = 0.08

# def moveit_error_string(code):
#     error_map = {
#         1: "SUCCESS",
#         -1: "FAILURE",
#         -2: "PLANNING_FAILED",
#         -3: "INVALID_MOTION_PLAN",
#         -4: "MOTION_PLAN_INVALIDATED_BY_ENVIRONMENT_CHANGE",
#         -5: "CONTROL_FAILED",
#         -6: "UNABLE_TO_AQUIRE_SENSOR_DATA",
#         -7: "TIMED_OUT",
#         -10: "START_STATE_IN_COLLISION",
#         -11: "START_STATE_VIOLATES_PATH_CONSTRAINTS",
#     }
#     return error_map.get(code, "UNKNOWN")


# ###############################################################################
# #            A CLASS TO PERFORM PICK AND PLACE STEPS (BUT SEPARATELY)
# ###############################################################################
# class PickAndPlaceManager(Node):
#     def __init__(self):
#         super().__init__('pick_and_place_manager')
#         # Action clients
#         self._move_client = ActionClient(self, MoveGroup, '/move_action')
#         self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
#         self._gripper_client = ActionClient(self, GripperCommand, 'gripper_controller/gripper_cmd')

#         # Wait for servers once
#         self._move_client.wait_for_server()
#         self._exec_client.wait_for_server()
#         self._gripper_client.wait_for_server()

#     def pick(self, cup_name):
#         """Pick only: approach object, open, descend, close, lift."""
#         if cup_name not in OBJECT_GOALS:
#             self.get_logger().error(f"Object '{cup_name}' not in OBJECT_GOALS.")
#             return False

#         data = OBJECT_GOALS[cup_name]
#         pick_pos = data["position"]
#         pick_orient = data["orientation"]

#         # 1) Open gripper
#         self.open_gripper()
#         time.sleep(2)

#         # 2) Approach above pick
#         approach_pick = pick_pos.copy()
#         approach_pick[2] += 0.097
#         if not self.move_ee_to_pose(approach_pick, pick_orient):
#             return False
#         time.sleep(2)

#         # 3) Descend to pick
#         if not self.move_ee_to_pose(pick_pos, pick_orient):
#             return False
#         time.sleep(2)

#         # 4) Close gripper
#         self.close_gripper()
#         time.sleep(2)

#         # 5) Lift back up
#         if not self.move_ee_to_pose(approach_pick, pick_orient):
#             return False
#         time.sleep(2)

#         self.get_logger().info(f"Successfully picked up '{cup_name}'")
#         return True

#     def place(self, cup_name, place_key):
#         """Place only: from current position => intermediate => final => open => lift => up."""
#         if cup_name not in OBJECT_GOALS:
#             self.get_logger().error(f"Object '{cup_name}' not in OBJECT_GOALS.")
#             return False
#         if place_key not in PLACE_GOAL:
#             self.get_logger().error(f"Place location '{place_key}' not in PLACE_GOAL.")
#             return False

#         place_data = PLACE_GOAL[place_key]
#         place_pos = place_data["position"]
#         place_orient = place_data["orientation"]

#         # 1) go to above the place position
#         approach_place = place_pos.copy()
#         approach_place[2] += 0.097
#         if not self.move_ee_to_pose(approach_place, place_orient):
#             return False
#         time.sleep(2)

#         # 2) Descend to final place
#         if not self.move_ee_to_pose(place_pos, place_orient):
#             return False
#         time.sleep(2)

#         # 3) Open the gripper
#         self.mid_gripper()
#         time.sleep(2)

#         if not self.move_ee_to_pose(approach_place, place_orient):
#             return False
#         time.sleep(2)

#         # 5) Move up to the "HOME" pose
#         if not self.move_ee_to_pose(PLACE_GOAL["HOME"]["position"],
#                                     PLACE_GOAL["HOME"]["orientation"]):
#             return False
#         time.sleep(2)

#         self.get_logger().info(f"Successfully placed '{cup_name}' at '{place_key}'")
#         return True

#     # --------------------------------------------------------------------------
#     # Helpers for gripper control & MoveIt
#     # --------------------------------------------------------------------------
#     def open_gripper(self):
#         self._send_gripper_cmd(GRIPPER_OPEN)

#     def mid_gripper(self):
#         self._send_gripper_cmd(GRIPPER_MIDDLE)

#     def close_gripper(self):
#         goal_msg = GripperCommand.Goal()
#         goal_msg.command.position = GRIPPER_CLOSE

#         send_goal_future = self._gripper_client.send_goal_async(goal_msg)
#         rclpy.spin_until_future_complete(self, send_goal_future)
#         goal_handle = send_goal_future.result()

#         if not goal_handle or not goal_handle.accepted:
#             self.get_logger().error("Gripper command rejected!")
#             return

#         start_time = time.time()
#         timeout = 60
#         result_future = goal_handle.get_result_async()

#         while rclpy.ok() and not result_future.done():
#             rclpy.spin_once(self, timeout_sec=0.1)
#             if time.time() - start_time > timeout:
#                 self.get_logger().warn("Gripper command timed out — continuing anyway.")
#                 return

#         result = result_future.result().result
#         if result.reached_goal:
#             self.get_logger().info("Gripper successfully closed.")
#         elif result.stalled:
#             self.get_logger().warn("Gripper stalled — might be blocked or fully closed.")
#         else:
#             self.get_logger().warn("Gripper did not reach goal, but did not stall either.")

#         time.sleep(2)

#     def _send_gripper_cmd(self, position):
#         goal_msg = GripperCommand.Goal()
#         goal_msg.command.position = position
#         goal_msg.command.max_effort = 100.0
#         self.get_logger().info(f"Gripper => position={position:.3f}, effort=100")

#         send_goal_future = self._gripper_client.send_goal_async(goal_msg)
#         rclpy.spin_until_future_complete(self, send_goal_future)
#         goal_handle = send_goal_future.result()

#         if not goal_handle or not goal_handle.accepted:
#             self.get_logger().error("Gripper command was rejected!")
#             return

#         # Wait for result
#         result_future = goal_handle.get_result_async()
#         rclpy.spin_until_future_complete(self, result_future)
#         result = result_future.result().result
#         self.get_logger().info(f"Gripper result: reached={result.reached_goal}, stalled={result.stalled}")

#     def move_ee_to_pose(self, position, orientation, sphere_radius=0.01, max_attempts=25):
#         goal_msg = MoveGroup.Goal()

#         request = MotionPlanRequest()
#         request.group_name = "ur_manipulator"
#         request.allowed_planning_time = 10.0
#         request.max_velocity_scaling_factor = 0.7
#         request.max_acceleration_scaling_factor = 0.7

#         constraints = Constraints()

#         # Position
#         pc = PositionConstraint()
#         pc.header.frame_id = "world"
#         pc.link_name = "tool0"
#         pc.weight = 1.0

#         sphere = SolidPrimitive()
#         sphere.type = SolidPrimitive.SPHERE
#         sphere.dimensions = [sphere_radius]

#         sphere_pose = Pose()
#         sphere_pose.position.x = position[0]
#         sphere_pose.position.y = position[1]
#         sphere_pose.position.z = position[2]
#         sphere_pose.orientation.w = 1.0  # orientation is enforced separately

#         pc.constraint_region.primitives.append(sphere)
#         pc.constraint_region.primitive_poses.append(sphere_pose)
#         constraints.position_constraints.append(pc)

#         arm_constraint = PositionConstraint()
#         arm_constraint.header.frame_id = "world"
#         arm_constraint.link_name = "forearm_link"
#         arm_constraint.weight = 1.0

#         z_box = SolidPrimitive()
#         z_box.type = SolidPrimitive.BOX
#         z_box.dimensions = [10.0, 10.0, 1.75]
#         z_box_pose = Pose()
#         z_box_pose.position.x = 0.0
#         z_box_pose.position.y = 0.0
#         z_box_pose.position.z = 2.125
#         z_box_pose.orientation.w = 1.0

#         arm_constraint.constraint_region.primitives.append(z_box)
#         arm_constraint.constraint_region.primitive_poses.append(z_box_pose)
#         constraints.position_constraints.append(arm_constraint)

#         # Orientation
#         oc = OrientationConstraint()
#         oc.header.frame_id = "world"
#         oc.link_name = "tool0"
#         oc.orientation.x = orientation[0]
#         oc.orientation.y = orientation[1]
#         oc.orientation.z = orientation[2]
#         oc.orientation.w = orientation[3]
#         oc.absolute_x_axis_tolerance = 0.1
#         oc.absolute_y_axis_tolerance = 0.1
#         oc.absolute_z_axis_tolerance = 0.1
#         oc.weight = 1.0

#         constraints.orientation_constraints.append(oc)
#         request.goal_constraints.append(constraints)

#         planning_options = PlanningOptions()
#         planning_options.planning_scene_diff.is_diff = True
#         planning_options.planning_scene_diff.robot_state.is_diff = True

#         goal_msg.request = request
#         goal_msg.planning_options = planning_options

#         for attempt in range(max_attempts):
#             self.get_logger().info(
#                 f"[{attempt+1}/{max_attempts}] Move to x={position[0]:.3f}, y={position[1]:.3f}, z={position[2]:.3f}"
#             )
#             future = self._move_client.send_goal_async(goal_msg)
#             rclpy.spin_until_future_complete(self, future)
#             goal_handle = future.result()

#             if not goal_handle or not goal_handle.accepted:
#                 self.get_logger().warn("MoveGroup goal was rejected.")
#                 time.sleep(0.5)
#                 continue

#             result_future = goal_handle.get_result_async()
#             rclpy.spin_until_future_complete(self, result_future)
#             result_msg = result_future.result()

#             if result_msg.result.error_code.val == 1:
#                 self.get_logger().info("Motion plan + execution succeeded!\n")
#                 return True
#             else:
#                 code = result_msg.result.error_code.val
#                 self.get_logger().warn(f"Motion failed with error {code} ({moveit_error_string(code)})")
#                 time.sleep(0.5)

#         self.get_logger().error("All attempts to plan this motion failed.")
#         return False


# ###############################################################################
# #                      LLM Node – Recognizing 3 Types of Commands
# ###############################################################################
# class LLMAndNavNode(Node):
#     """
#     Polls user input, sends to an LLM, and based on the LLM’s response:
#      - If it indicates “pick,” do a pick with extracted color (or default).
#      - If it indicates “place,” do a place with extracted location (or default).
#      - If it indicates “pick and place,” do both in sequence.
#      - If the user only says “place,” we use the currently_held_item from a prior pick.
#     """

#     def __init__(self):
#         super().__init__('llm_node')

#         # For calling OpenAI
#         openai.api_key = os.getenv("OPENAI_API_KEY", "sk- ..")
#         self.get_logger().info("LLM node started")

#         # We'll hold the name of the last item we picked (if any)
#         self.currently_held_item = None

#         # We'll create our pick/place manager node
#         self.pick_place_mgr = PickAndPlaceManager()

#         # Timer to poll user from the console every 5 seconds
#         self.busy = False
#         self.poll_timer = self.create_timer(5.0, self.poll_user)
#         self.get_logger().info("Ready for user commands...")

#     def poll_user(self):
#         if self.busy:
#             return
#         self.busy = True
#         try:
#             user_text = input("\nCommand (e.g., 'Pick up the red cup' OR 'Place it in BB'): ").strip()
#             if not user_text:
#                 return

#             # 1) Query the LLM to interpret
#             response = self.query_llm(user_text)
#             self.get_logger().info(f"LLM response: {response}")

#             # 2) From the LLM text, figure out if user wants pick and/or place
#             do_pick = ("pick" in response.lower())
#             do_place = ("place" in response.lower())

#             # Extract color (which cup) from text (if any)
#             color = self.extract_color(response)
#             # Extract location (which place key) from text (if any)
#             location = self.extract_location(response)

#             # # Some defaults
#             # if do_pick and not color:
#             #     color = "RedCup"  # fallback color
#             # if do_place and not location:
#             #     location = "BB"   # fallback place

#             if do_pick and do_place:
#                 # Example: "Pick up the green cup and place it on AA"
#                 self.do_pick_and_place(color, location)

#             elif do_pick and not do_place:
#                 # Example: "Pick up the red cup" => pick only
#                 self.do_pick_only(color)

#             elif do_place and not do_pick:
#                 # Example: "Place the item in CC"
#                 # Use the currently_held_item if user hasn't specified a color
#                 if not color:
#                     color = self.currently_held_item

#                 self.do_place_only(color, location)
#             else:
#                 # The user said something the LLM didn't interpret as pick or place
#                 self.get_logger().warn("No recognized pick/place action from LLM response.")

#         except Exception as e:
#             self.get_logger().error(f"Error in command: {e}")
#         finally:
#             self.busy = False

#     # --------------------------------------------------------------------------
#     # Concrete methods to do pick or place
#     # --------------------------------------------------------------------------
#     def do_pick_only(self, cup_name):
#         if not cup_name:
#             self.get_logger().error("LLM says to pick, but no item was determined!")
#             return
#         ok = self.pick_place_mgr.pick(cup_name)
#         if ok:
#             self.currently_held_item = cup_name  # store what we're holding now

#     def do_place_only(self, cup_name, place_key):
#         if not cup_name:
#             self.get_logger().error("Tried to place, but we don't know which item (none held?).")
#             return
#         ok = self.pick_place_mgr.place(cup_name, place_key)
#         if ok:
#             # Once placed, we're not holding anything
#             self.currently_held_item = None

#     def do_pick_and_place(self, cup_name, place_key):
#         # First pick
#         ok_pick = self.pick_place_mgr.pick(cup_name)
#         if not ok_pick:
#             return
#         self.currently_held_item = cup_name

#         # Then place
#         ok_place = self.pick_place_mgr.place(cup_name, place_key)
#         if ok_place:
#             self.currently_held_item = None

#     # --------------------------------------------------------------------------
#     # LLM handling
#     # --------------------------------------------------------------------------
#     def query_llm(self, user_text):
#         """
#         Send user_text to GPT-3.5 or GPT-4 to interpret. 
#         In a real system, you'd craft the system prompt carefully to ensure
#         the LLM response is short, e.g. "User wants to: pick or place. Cup color? Place location?"
#         """
#         try:
#             resp = openai.chat.completions.create(
#                 model="gpt-3.5-turbo",
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": (
#                             "You control a robot that can pick up and place colored cups. "
#                             "Available cups: RedCup, GreenCup, BlueCup, YellowCup, PurpleCup. "
#                             "Available places: A, B, C, AA, BB, CC, etc. "
#                             "The user might say things like 'pick up the red cup' or 'place it in AA', or both. "
#                             "Your job is to interpret their intent and respond with a short structured sentence including the keywords: 'pick', 'place', the color (e.g. 'red'), and the location (e.g. 'AA'). "
#                             "Fix minor spelling mistakes in cup colors and locations. "
#                             "If you are uncertain about the color or location, or the user's message is ambiguous, ask for clarification with a short question like: 'Did you mean the blue cup?' or 'Where should I place the cup?'. "
#                             "Only ask one clarifying question at a time if needed."
#                         )
#                     },
#                     {"role": "user", "content": user_text},
#                 ],
#                 temperature=0.0
#             )
#             return resp.choices[0].message.content
#         except Exception as e:
#             self.get_logger().error(f"LLM error: {str(e)}")
#             return user_text  # fallback: just use user text

#     def extract_color(self, text):
#         """Look for known color words in the LLM response."""
#         lower = text.lower()
#         for c in ["red", "green", "blue", "yellow", "purple"]:
#             if c in lower:
#                 # Return e.g. 'RedCup'
#                 return c.capitalize() + "Cup"
#         return None

#     def extract_location(self, text):
#         """Look for a known location (A,B,C,AA,BB,CC, etc.) in the text."""
#         for place in PLACE_GOAL.keys():
#             # place is e.g. 'A', 'B', 'CC', 'HOME', etc.
#             if place.lower() in text.lower():
#                 return place
#         return None


# ###############################################################################
# #                               MAIN
# ###############################################################################
# def main(args=None):
#     rclpy.init(args=args)
#     node = LLMAndNavNode()

#     try:
#         rclpy.spin(node)
#     except KeyboardInterrupt:
#         pass
#     finally:
#         # Destroy the main node, also pick_place_mgr is a child node inside it
#         node.pick_place_mgr.destroy_node()
#         node.destroy_node()
#         rclpy.shutdown()

# if __name__ == "__main__":
#     main()






































































import os
import sys
import time
import re

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import Pose
from shape_msgs.msg import SolidPrimitive
from control_msgs.action import GripperCommand
from moveit_msgs.action import MoveGroup, ExecuteTrajectory
from moveit_msgs.msg import (
    MotionPlanRequest,
    Constraints,
    PositionConstraint,
    OrientationConstraint,
    PlanningOptions
)
import openai

###############################################################################
#                            SHARED DICTIONARIES
###############################################################################
OBJECT_GOALS = {
    "RedCup": {
        "position": [0.9226, 1.2018, 1.368],
        "orientation": [0.739, 0.673, 0.014, -0.023],
    },
    "GreenCup": {
        "position": [1.184, 1.281, 1.384],
        "orientation": [0.739, 0.673, 0.014, -0.023],
    },
    "BlueCup": {
        "position": [1.46, 1.203, 1.368],
        "orientation": [0.739, 0.673, 0.014, -0.023],
    },
    "YellowCup": {
        "position": [0.99, 1.427, 1.368],
        "orientation": [0.739, 0.673, 0.014, -0.023],
    },
    "PurpleCup": {
        "position": [1.385, 1.393, 1.368],
        "orientation": [0.739, 0.673, 0.014, -0.023],
    },
}

PLACE_GOAL = {
    "TrialPlaceGoal": {
        "position": [1.154, 0.249, 1.293],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "TestConfig": {
        "position": [1.154, 0.288, 1.604],
        "orientation": [-0.040, 0.996, 0.076, -0.009]
    },
    "HOME": {
        "position": [1.061, 0.542, 2.101],
        "orientation": [0.000, -0.707, 0.707, 0.000]
    },
    "A": {
        "position": [1.42, -0.042, 1.35],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "B": {
        "position": [1.113, -0.037, 1.35],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "C": {
        "position": [0.839, -0.0514, 1.35],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "AA": {
        "position": [1.43, 0.215, 1.35],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "BB": {
        "position": [1.131, 0.22, 1.35],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "CC": {
        "position": [0.83, 0.21, 1.35],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
}

###############################################################################
#                          GRIPPER CONSTANTS
###############################################################################
GRIPPER_OPEN = 0.004
GRIPPER_MIDDLE = 0.06
GRIPPER_CLOSE = 0.08

def moveit_error_string(code):
    error_map = {
        1: "SUCCESS",
        -1: "FAILURE",
        -2: "PLANNING_FAILED",
        -3: "INVALID_MOTION_PLAN",
        -4: "MOTION_PLAN_INVALIDATED_BY_ENVIRONMENT_CHANGE",
        -5: "CONTROL_FAILED",
        -6: "UNABLE_TO_AQUIRE_SENSOR_DATA",
        -7: "TIMED_OUT",
        -10: "START_STATE_IN_COLLISION",
        -11: "START_STATE_VIOLATES_PATH_CONSTRAINTS",
    }
    return error_map.get(code, "UNKNOWN")


###############################################################################
#            A CLASS TO PERFORM PICK AND PLACE STEPS (BUT SEPARATELY)
###############################################################################
class PickAndPlaceManager(Node):
    def __init__(self):
        super().__init__('pick_and_place_manager')
        # Action clients
        self._move_client = ActionClient(self, MoveGroup, '/move_action')
        self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        self._gripper_client = ActionClient(self, GripperCommand, 'gripper_controller/gripper_cmd')

        # Wait for servers once
        self._move_client.wait_for_server()
        self._exec_client.wait_for_server()
        self._gripper_client.wait_for_server()

    def pick(self, cup_name):
        """Pick only: approach object, open, descend, close, lift."""
        if cup_name not in OBJECT_GOALS:
            self.get_logger().error(f"Object '{cup_name}' not in OBJECT_GOALS.")
            return False

        data = OBJECT_GOALS[cup_name]
        pick_pos = data["position"]
        pick_orient = data["orientation"]

        # 1) Open gripper
        self.open_gripper()
        time.sleep(2)

        # 2) Approach above pick
        approach_pick = pick_pos.copy()
        approach_pick[2] += 0.097
        if not self.move_ee_to_pose(approach_pick, pick_orient):
            return False
        time.sleep(2)

        # 3) Descend to pick
        if not self.move_ee_to_pose(pick_pos, pick_orient):
            return False
        time.sleep(2)

        # 4) Close gripper
        self.close_gripper()
        time.sleep(2)

        # 5) Lift back up
        if not self.move_ee_to_pose(approach_pick, pick_orient):
            return False
        time.sleep(2)

        self.get_logger().info(f"Successfully picked up '{cup_name}'")
        return True

    def place(self, cup_name, place_key):
        """Place only: from current position => intermediate => final => open => lift => up."""
        if cup_name not in OBJECT_GOALS:
            self.get_logger().error(f"Object '{cup_name}' not in OBJECT_GOALS.")
            return False
        if place_key not in PLACE_GOAL:
            self.get_logger().error(f"Place location '{place_key}' not in PLACE_GOAL.")
            return False

        place_data = PLACE_GOAL[place_key]
        place_pos = place_data["position"]
        place_orient = place_data["orientation"]

        approach_place = place_pos.copy()
        approach_place[2] += 0.097
        
        # 1) Move up to the "safe" pose (TestConfig)
        # if not self.move_ee_to_pose(PLACE_GOAL["TestConfig"]["position"],
        #                             PLACE_GOAL["TestConfig"]["orientation"]):
        #     return False
        # time.sleep(2)
        
        # 2) go to above the place position
        self.get_logger().info(f"AA pose: {place_pos}, approach: {approach_place}")
        if not self.move_ee_to_pose(approach_place, place_orient):
            return False
        time.sleep(2)

        # 3) Descend to final place
        if not self.move_ee_to_pose(place_pos, place_orient):
            return False
        time.sleep(2)

        # 4) Open the gripper
        self.mid_gripper()
        time.sleep(2)
        
        # 5) move above the place position again
        if not self.move_ee_to_pose(approach_place, place_orient):
            return False
        time.sleep(2)

        # 5) Move up to the "HOME" pose
        if not self.move_ee_to_pose(PLACE_GOAL["HOME"]["position"],
                                    PLACE_GOAL["HOME"]["orientation"]):
            return False
        time.sleep(2)

        self.get_logger().info(f"Successfully placed '{cup_name}' at '{place_key}'")
        return True

    # --------------------------------------------------------------------------
    # Helpers for gripper control & MoveIt
    # --------------------------------------------------------------------------
    def open_gripper(self):
        self._send_gripper_cmd(GRIPPER_OPEN)

    def mid_gripper(self):
        self._send_gripper_cmd(GRIPPER_MIDDLE)

    def close_gripper(self):
        goal_msg = GripperCommand.Goal()
        goal_msg.command.position = GRIPPER_CLOSE

        send_goal_future = self._gripper_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()

        if not goal_handle or not goal_handle.accepted:
            self.get_logger().error("Gripper command rejected!")
            return

        start_time = time.time()
        timeout = 60
        result_future = goal_handle.get_result_async()

        while rclpy.ok() and not result_future.done():
            rclpy.spin_once(self, timeout_sec=0.1)
            if time.time() - start_time > timeout:
                self.get_logger().warn("Gripper command timed out — continuing anyway.")
                return

        result = result_future.result().result
        if result.reached_goal:
            self.get_logger().info("Gripper successfully closed.")
        elif result.stalled:
            self.get_logger().warn("Gripper stalled — might be blocked or fully closed.")
        else:
            self.get_logger().warn("Gripper did not reach goal, but did not stall either.")

        time.sleep(2)

    def _send_gripper_cmd(self, position):
        goal_msg = GripperCommand.Goal()
        goal_msg.command.position = position
        goal_msg.command.max_effort = 100.0
        self.get_logger().info(f"Gripper => position={position:.3f}, effort=100")

        send_goal_future = self._gripper_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()

        if not goal_handle or not goal_handle.accepted:
            self.get_logger().error("Gripper command was rejected!")
            return

        # Wait for result
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result().result
        self.get_logger().info(f"Gripper result: reached={result.reached_goal}, stalled={result.stalled}")

    def move_ee_to_pose(self, position, orientation, sphere_radius=0.01, max_attempts=25):
        goal_msg = MoveGroup.Goal()

        request = MotionPlanRequest()
        request.group_name = "ur_manipulator"
        request.allowed_planning_time = 10.0
        request.max_velocity_scaling_factor = 0.7
        request.max_acceleration_scaling_factor = 0.7

        constraints = Constraints()

        # Position
        pc = PositionConstraint()
        pc.header.frame_id = "world"
        pc.link_name = "tool0"
        pc.weight = 1.0

        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [sphere_radius]

        sphere_pose = Pose()
        sphere_pose.position.x = position[0]
        sphere_pose.position.y = position[1]
        sphere_pose.position.z = position[2]
        sphere_pose.orientation.w = 1.0  # orientation is enforced separately

        pc.constraint_region.primitives.append(sphere)
        pc.constraint_region.primitive_poses.append(sphere_pose)
        constraints.position_constraints.append(pc)

        arm_constraint = PositionConstraint()
        arm_constraint.header.frame_id = "world"
        arm_constraint.link_name = "forearm_link"
        arm_constraint.weight = 1.0

        z_box = SolidPrimitive()
        z_box.type = SolidPrimitive.BOX
        z_box.dimensions = [10.0, 10.0, 1.75]
        z_box_pose = Pose()
        z_box_pose.position.x = 0.0
        z_box_pose.position.y = 0.0
        z_box_pose.position.z = 2.3
        z_box_pose.orientation.w = 1.0

        arm_constraint.constraint_region.primitives.append(z_box)
        arm_constraint.constraint_region.primitive_poses.append(z_box_pose)
        constraints.position_constraints.append(arm_constraint)

        # Orientation
        oc = OrientationConstraint()
        oc.header.frame_id = "world"
        oc.link_name = "tool0"
        oc.orientation.x = orientation[0]
        oc.orientation.y = orientation[1]
        oc.orientation.z = orientation[2]
        oc.orientation.w = orientation[3]
        oc.absolute_x_axis_tolerance = 0.1
        oc.absolute_y_axis_tolerance = 0.1
        oc.absolute_z_axis_tolerance = 0.1
        oc.weight = 1.0

        constraints.orientation_constraints.append(oc)
        request.goal_constraints.append(constraints)

        planning_options = PlanningOptions()
        planning_options.planning_scene_diff.is_diff = True
        planning_options.planning_scene_diff.robot_state.is_diff = True

        goal_msg.request = request
        goal_msg.planning_options = planning_options

        for attempt in range(max_attempts):
            self.get_logger().info(
                f"[{attempt+1}/{max_attempts}] Move to x={position[0]:.3f}, y={position[1]:.3f}, z={position[2]:.3f}"
            )
            future = self._move_client.send_goal_async(goal_msg)
            rclpy.spin_until_future_complete(self, future)
            goal_handle = future.result()

            if not goal_handle or not goal_handle.accepted:
                self.get_logger().warn("MoveGroup goal was rejected.")
                time.sleep(0.5)
                continue

            result_future = goal_handle.get_result_async()
            rclpy.spin_until_future_complete(self, result_future)
            result_msg = result_future.result()

            if result_msg.result.error_code.val == 1:
                self.get_logger().info("Motion plan + execution succeeded!\n")
                return True
            else:
                code = result_msg.result.error_code.val
                self.get_logger().warn(f"Motion failed with error {code} ({moveit_error_string(code)})")
                time.sleep(0.5)

        self.get_logger().error("All attempts to plan this motion failed.")
        return False


###############################################################################
#                      LLM Node – Recognizing 3 Types of Commands
###############################################################################
class LLMAndNavNode(Node):
    """
    Polls user input, sends to an LLM, and based on the LLM’s response:
     - If it indicates “pick,” do a pick with extracted color (or default).
     - If it indicates “place,” do a place with extracted location (or default).
     - If it indicates “pick and place,” do both in sequence.
     - If the user only says “place,” we use the currently_held_item from a prior pick.
    """
class LLMAndNavNode(Node):
    # def __init__(self):
    #     super().__init__('llm_node')

    #     # For calling OpenAI
    #     openai.api_key = os.getenv("OPENAI_API_KEY", "sk- ..")
    #     self.get_logger().info("LLM node started")

    #     # We'll hold the name of the last item we picked (if any)
    #     self.currently_held_item = None

    #     # We'll create our pick/place manager node
    #     self.pick_place_mgr = PickAndPlaceManager()

    #     # Timer to poll user from the console every 5 seconds
    #     self.busy = False
    #     self.poll_timer = self.create_timer(5.0, self.poll_user)
    #     self.get_logger().info("Ready for user commands...")
    def __init__(self):
        super().__init__('llm_node')

        # For calling OpenAI
        openai.api_key = os.getenv("OPENAI_API_KEY", "sk- ..")
        self.get_logger().info("LLM node started")

        self.currently_held_item = None
        self.pick_place_mgr = PickAndPlaceManager()

        # NEW: Chat memory and clarification flag
        self.chat_history = []
        self.awaiting_clarification = False

        self.busy = False
        self.poll_timer = self.create_timer(5.0, self.poll_user)
        self.get_logger().info("Ready for user commands...")

    # def poll_user(self):
    #     if self.busy:
    #         return
    #     self.busy = True
    #     try:
    #         user_text = input("\nCommand (e.g., 'Pick up the red cup' OR 'Place it in BB'): ").strip()
    #         if not user_text:
    #             return

    #         # 1) Query the LLM to interpret
    #         response = self.query_llm(user_text)
    #         self.get_logger().info(f"LLM response: {response}")

    #         # 2) From the LLM text, figure out if user wants pick and/or place
    #         do_pick = ("pick" in response.lower())
    #         do_place = ("place" in response.lower())

    #         # Extract color (which cup) from text (if any)
    #         color = self.extract_color(response)
    #         # Extract location (which place key) from text (if any)
    #         location = self.extract_location(response)

    #         # # Some defaults
    #         # if do_pick and not color:
    #         #     color = "RedCup"  # fallback color
    #         # if do_place and not location:
    #         #     location = "BB"   # fallback place

    #         if do_pick and do_place:
    #             # Example: "Pick up the green cup and place it on AA"
    #             self.do_pick_and_place(color, location)

    #         elif do_pick and not do_place:
    #             # Example: "Pick up the red cup" => pick only
    #             self.do_pick_only(color)

    #         elif do_place and not do_pick:
    #             # Example: "Place the item in CC"
    #             # Use the currently_held_item if user hasn't specified a color
    #             if not color:
    #                 color = self.currently_held_item

    #             self.do_place_only(color, location)
    #         else:
    #             # The user said something the LLM didn't interpret as pick or place
    #             self.get_logger().warn("No recognized pick/place action from LLM response.")

    #     except Exception as e:
    #         self.get_logger().error(f"Error in command: {e}")
    #     finally:
    #         self.busy = False

    def poll_user(self):
        if self.busy:
            return
        self.busy = True
        try:
            user_text = input("\nCommand (e.g., 'Pick up the red cup' OR 'Place it in BB'): ").strip()
            if not user_text:
                return

            self.chat_history.append({"role": "user", "content": user_text})
            response = self.query_llm()
            self.chat_history.append({"role": "assistant", "content": response})
            self.get_logger().info(f"LLM response: {response}")

            # If LLM is asking a clarification question, wait for next input
            if response.strip().endswith("?"):
                self.awaiting_clarification = True
                return
            else:
                self.awaiting_clarification = False

            do_pick = ("pick" in response.lower())
            do_place = ("place" in response.lower())

            color = self.extract_color(response)
            location = self.extract_location(response)

            if do_pick and do_place:
                self.do_pick_and_place(color, location)
            elif do_pick and not do_place:
                self.do_pick_only(color)
            elif do_place and not do_pick:
                if not color:
                    color = self.currently_held_item
                self.do_place_only(color, location)
            else:
                self.get_logger().warn("No recognized pick/place action from LLM response.")

        except Exception as e:
            self.get_logger().error(f"Error in command: {e}")
        finally:
            self.busy = False
            
    # --------------------------------------------------------------------------
    # Concrete methods to do pick or place
    # --------------------------------------------------------------------------
    def do_pick_only(self, cup_name):
        if not cup_name:
            self.get_logger().error("LLM says to pick, but no item was determined!")
            return
        ok = self.pick_place_mgr.pick(cup_name)
        if ok:
            self.currently_held_item = cup_name  # store what we're holding now

    def do_place_only(self, cup_name, place_key):
        if not cup_name:
            self.get_logger().error("Tried to place, but we don't know which item (none held?).")
            return
        ok = self.pick_place_mgr.place(cup_name, place_key)
        if ok:
            # Once placed, we're not holding anything
            self.currently_held_item = None

    def do_pick_and_place(self, cup_name, place_key):
        # First pick
        ok_pick = self.pick_place_mgr.pick(cup_name)
        if not ok_pick:
            return
        self.currently_held_item = cup_name

        # Then place
        ok_place = self.pick_place_mgr.place(cup_name, place_key)
        if ok_place:
            self.currently_held_item = None

    # --------------------------------------------------------------------------
    # LLM handling
    # --------------------------------------------------------------------------
    
    # def query_llm(self, user_text):
    #     """
    #     Send user_text to GPT-3.5 or GPT-4 to interpret. 
    #     In a real system, you'd craft the system prompt carefully to ensure
    #     the LLM response is short, e.g. "User wants to: pick or place. Cup color? Place location?"
    #     """
    #     try:
    #         resp = openai.chat.completions.create(
    #             model="gpt-3.5-turbo",
    #             messages=[
    #                 {
    #                     "role": "system",
    #                     "content": (
    #                         "You control a robot that can pick up and place colored cups. "
    #                         "Available cups: RedCup, GreenCup, BlueCup, YellowCup, PurpleCup. "
    #                         "Available places: A, B, C, AA, BB, CC, etc. "
    #                         "The user might say things like 'pick up the red cup' or 'place it in AA', or both. "
    #                         "Your job is to interpret their intent and respond with a short structured sentence including the keywords: 'pick', 'place', the color (e.g. 'red'), and the location (e.g. 'AA'). "
    #                         "Fix minor spelling mistakes in cup colors and locations. "
    #                         "If you are uncertain about the color or location, or the user's message is ambiguous, ask for clarification with a short question like: 'Did you mean the blue cup?' or 'Where should I place the cup?'. "
    #                         "Only ask one clarifying question at a time if needed."
    #                     )
    #                 },
    #                 {"role": "user", "content": user_text},
    #             ],
    #             temperature=0.0
    #         )
    #         return resp.choices[0].message.content
    #     except Exception as e:
    #         self.get_logger().error(f"LLM error: {str(e)}")
    #         return user_text  # fallback: just use user text
        
    def query_llm(self):
        try:
            resp = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": (
                        "You control a robot that can pick up and place colored cups. "
                        "Available cups: RedCup, GreenCup, BlueCup, YellowCup, PurpleCup. "
                        "Available places: A, B, C, AA, BB, CC, etc. "
                        "The user might say things like 'pick up the red cup' or 'place it in AA', or both. "
                        "Your job is to interpret their intent and respond with a short structured sentence including the keywords: 'pick', 'place', the color (e.g. 'red'), and the location (e.g. 'AA'). "
                        "Fix minor spelling mistakes in cup colors and locations. "
                        "If you are uncertain about the color or location, or the user's message is ambiguous, ask for clarification with a short question like: 'Did you mean the blue cup?' or 'Where should I place the cup?'. "
                        "Only ask one clarifying question at a time if needed."
                    )},
                    *self.chat_history
                ],
                temperature=0.0
            )
            return resp.choices[0].message.content
        except Exception as e:
            self.get_logger().error(f"LLM error: {str(e)}")
            return "I'm sorry, something went wrong."

    def extract_color(self, text):
        """Look for known color words in the LLM response."""
        lower = text.lower()
        for c in ["red", "green", "blue", "yellow", "purple"]:
            if c in lower:
                # Return e.g. 'RedCup'
                return c.capitalize() + "Cup"
        return None
    
    def extract_location(self, text):
        lower_text = text.lower()
        # Sort by length descending to match AA before A, BB before B
        for place in sorted(PLACE_GOAL.keys(), key=lambda x: -len(x)):
            pattern = r'\b' + re.escape(place.lower()) + r'\b'
            if re.search(pattern, lower_text):
                return place
        return None

###############################################################################
#                               MAIN
###############################################################################
def main(args=None):
    rclpy.init(args=args)
    node = LLMAndNavNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Destroy the main node, also pick_place_mgr is a child node inside it
        node.pick_place_mgr.destroy_node()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
