#!/usr/bin/env python3
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
    PlanningOptions,
    PlanningScene,
    AttachedCollisionObject ,
    CollisionObject
)
# import openai
from openai import OpenAI

# coordinates of target objects and goal positions
OBJECT_GOALS = {
    "RedCup": {
        "position": [0.913, 1.234, 1.35],
        "orientation": [0.730, 0.682, 0.028, -0.025],
    },
    "GreenCup": {
        "position": [1.195, 1.287, 1.35],
        "orientation": [0.730, 0.683, 0.028, -0.025],
    },
    "BlueCup": {
        "position": [1.463, 1.215, 1.35],
        "orientation": [0.728, 0.685, 0.025, -0.023],
    },
    "YellowCup": {
        "position": [0.985, 1.444, 1.35],
        "orientation": [0.739, 0.673, 0.014, -0.023],
    },
    "PurpleCup": {
        "position": [1.384, 1.398, 1.35],
        "orientation": [0.730, 0.683, 0.028, -0.025],
    },
}

EXTRA_LOCATIONS = {
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
    }
}
PLACE_GOAL = {
    "A": {
        "position": [1.457, -0.020, 1.35],
        "orientation": [0.728, 0.685, 0.023, -0.019]
    },
    "B": {
        "position": [1.143, -0.020, 1.35],
        "orientation": [0.728, 0.684, 0.023, -0.020]
    },
    "C": {
        "position": [0.777, -0.020, 1.35],
        "orientation": [0.728, 0.684, 0.034, -0.008]
    },
    "AA": {
        "position": [1.457, 0.185, 1.35],
        "orientation": [0.728, 0.685, 0.022, -0.020]
    },
    "BB": {
        "position": [1.143, 0.185, 1.35],
        "orientation": [0.728, 0.685, 0.023, -0.020]
    },
    "CC": {
        "position": [0.777, 0.185, 1.35],
        "orientation": [0.728, 0.684, 0.034, -0.008]
    },
}

GRIPPER_OPEN = 0.004
GRIPPER_MIDDLE = 0.04
GRIPPER_CLOSE = 0.083

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


# pick and place, motion control class
class PickAndPlaceManager(Node):
    def __init__(self):
        super().__init__('pick_and_place_manager')
        self.scene_pub = self.create_publisher(PlanningScene, '/planning_scene', 10)  # ✅ ADD THIS
        # Action clients
        self._move_client = ActionClient(self, MoveGroup, '/move_action')
        self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        self._gripper_client = ActionClient(self, GripperCommand, 'gripper_controller/gripper_cmd')

        # Wait for servers once
        self._move_client.wait_for_server()
        self._exec_client.wait_for_server()
        self._gripper_client.wait_for_server()
    
    # TF broadcasting fucntions
    def attach_object(self, object_id="my_cylinder", link_name="finger_left"):
        aco = AttachedCollisionObject()
        aco.link_name = link_name
        aco.object.id = object_id
        aco.object.header.frame_id = link_name
        aco.object.operation = CollisionObject.ADD

        prim = SolidPrimitive()
        prim.type = SolidPrimitive.CYLINDER
        prim.dimensions = [0.05, 0.035]
        aco.object.primitives.append(prim)

        link_pose = Pose()
        link_pose.position.z = 0.14
        link_pose.position.y = 0.05
        link_pose.orientation.w = 1.0
        aco.object.primitive_poses.append(link_pose)

        scene_msg = PlanningScene()
        scene_msg.is_diff = True
        scene_msg.robot_state.attached_collision_objects.append(aco)
        scene_msg.robot_state.is_diff = True

        self.get_logger().info(f"Attaching object '{object_id}'")
        self.scene_pub.publish(scene_msg)
        time.sleep(1.0)

    def detach_object(self, object_id="my_cylinder", link_name="finger_left"):
        aco = AttachedCollisionObject()
        aco.link_name = link_name
        aco.object.id = object_id
        aco.object.header.frame_id = link_name
        aco.object.operation = CollisionObject.REMOVE

        scene_msg = PlanningScene()
        scene_msg.is_diff = True
        scene_msg.robot_state.attached_collision_objects.append(aco)
        scene_msg.robot_state.is_diff = True

        self.get_logger().info(f"Detaching object '{object_id}'")
        self.scene_pub.publish(scene_msg)
        time.sleep(1.0)
        
    def remove_object(self, object_id="my_cylinder"):
        co = CollisionObject()
        co.id = object_id
        co.header.frame_id = "world"
        co.operation = CollisionObject.REMOVE

        scene_msg = PlanningScene()
        scene_msg.is_diff = True
        scene_msg.world.collision_objects.append(co)

        self.get_logger().info(f"Removing object '{object_id}' from scene")
        self.scene_pub.publish(scene_msg)
        time.sleep(1.0)
    
    # Robotic arm contorl fucntions
    def pick(self, cup_name):
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
        approach_pick[2] += 0.15
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
        
        self.attach_object(object_id=cup_name)

        self.get_logger().info(f"Successfully picked up '{cup_name}'")
        return True

    def place(self, cup_name, place_key):
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
        approach_place[2] += 0.15
        
        # 2) go to above the place position
        if not self.move_ee_to_pose(approach_place, place_orient):
            return False
        time.sleep(2)

        # 3) Descend to final place
        if not self.move_ee_to_pose(place_pos, place_orient):
            return False
        time.sleep(2)
        
        self.detach_object(object_id=cup_name)
        self.remove_object(object_id=cup_name)

        # 4) Open the gripper
        self.mid_gripper()
        time.sleep(2)
        
        # 5) move above the place position again
        if not self.move_ee_to_pose(approach_place, place_orient):
            return False
        time.sleep(2)

        self.get_logger().info(f"Successfully placed '{cup_name}' at '{place_key}'")
        return True
    
    # gripper contorl functions
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
        timeout = 15
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

    # main function to move arm 
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
        sphere_pose.orientation.w = 1.0
        
        pc.constraint_region.primitives.append(sphere)
        pc.constraint_region.primitive_poses.append(sphere_pose)
        constraints.position_constraints.append(pc)

        arm_constraint = PositionConstraint()
        arm_constraint.header.frame_id = "world"
        arm_constraint.link_name = "forearm_link"
        arm_constraint.weight = 1.0

        z_box = SolidPrimitive()
        z_box.type = SolidPrimitive.BOX
        z_box.dimensions = [10.0, 10.0, 1.7]
        z_box_pose = Pose()
        z_box_pose.position.x = 0.0
        z_box_pose.position.y = 0.0
        z_box_pose.position.z = 2.1
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

# LLM class
class LLMNode(Node):
    def __init__(self):
        super().__init__('llm_node')

        # For calling OpenAI
        # openai.api_key = os.getenv("OPENAI_API_KEY")
        # self.get_logger().info("LLM node started")
        
        self.currently_held_item = None
        self.pick_place_mgr = PickAndPlaceManager()

        self.chat_history = []
        self.awaiting_clarification = False

        self.busy = False
        self.poll_timer = self.create_timer(5.0, self.poll_user)
        
        self.slot_coordinates = {
            slot: (data["position"][0], data["position"][1])  # X, Y only
            for slot, data in PLACE_GOAL.items()
        }
        
        self.slot_info = "\n".join([
            f"{slot}: X={coord[0]:.3f}, Y={coord[1]:.3f}"
            for slot, coord in self.slot_coordinates.items()
        ])
        
        welcome_text = self.get_welcome_message_from_gpt()
        self.get_logger().info(f"\n{welcome_text}")

    def get_welcome_message_from_gpt(self):
        self.chat_history.append({"role": "user", "content": ""})  # or "Start conversation" if you prefer
        response = self.query_llm()
        self.chat_history.append({"role": "assistant", "content": response})
        return response
    
    def poll_user(self):
        if self.busy:
            return
        self.busy = True
        try:
            user_text = input("\nCommand: ").strip()           
            if not user_text:
                return
            
            # Hard-coded exit fallback
            if user_text.lower() in ["quit", "exit"]:
                self.get_logger().info("Console says 'quit'. Exiting now.")
                self.stop_and_exit()
                return

            self.chat_history.append({"role": "user", "content": user_text})
            response = self.query_llm()
            self.chat_history.append({"role": "assistant", "content": response})
            self.get_logger().info(f"LLM response: {response}\n")

            if "exit" in response.lower():
                self.get_logger().info("GPT requested exit. Stopping everything.")
                self.stop_and_exit()
                return
            
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

            if do_pick and not do_place and not color:
                self.get_logger().info("I'm not sure which color you meant. Could you clarify?")
                return

            if "step" in response.lower():
                self.handle_multi_step(response)
            elif do_pick and do_place:
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
    
    def stop_and_exit(self):
        self.poll_timer.cancel()
        self.destroy_node()
        self.pick_place_mgr.destroy_node()
        sys.exit(0)
    
    def handle_multi_step(self, response: str):
        step_pattern = r"Step\s*\d+:\s*(.*)"
        step_lines = re.findall(step_pattern, response, re.IGNORECASE)

        if not step_lines:
            self.get_logger().warn("No valid steps found in response.")
            return

        for i, line in enumerate(step_lines, 1):
            lower = line.lower()
            cup = self.extract_color(line)
            slot = self.extract_location(line)

            # Pick + Place
            if "pick" in lower and "place" in lower and cup and slot:
                self.get_logger().info(f"Step {i}: Pick {cup}, Place in {slot} \n")
                ok_pick = self.pick_place_mgr.pick(cup)
                if not ok_pick:
                    self.get_logger().error(f"Step {i}: Failed to pick {cup}")
                    break
                self.currently_held_item = cup

                ok_place = self.pick_place_mgr.place(cup, slot)
                if not ok_place:
                    self.get_logger().error(f"Step {i}: Failed to place {cup} in {slot} \n")
                    break
                self.currently_held_item = None

            # Pick only
            elif "pick" in lower and cup:
                self.get_logger().info(f"Step {i}: Pick {cup} \n")
                ok = self.pick_place_mgr.pick(cup)
                if ok:
                    self.currently_held_item = cup
                else:
                    self.get_logger().error(f"Step {i}: Failed to pick {cup}")
                    break

            # Place only
            elif "place" in lower and slot:
                if not self.currently_held_item:
                    self.get_logger().warn(f"Step {i}: No item currently held to place. \n")
                    break
                self.get_logger().info(f"Step {i}: Place {self.currently_held_item} in {slot} \n")
                ok = self.pick_place_mgr.place(self.currently_held_item, slot)
                if ok:
                    self.currently_held_item = None
                else:
                    self.get_logger().error(f"Step {i}: Failed to place item in {slot}")
                    break

            else:
                self.get_logger().warn(f"Step {i}: Could not interpret action for line: {line}")

            
    # methods to do pick or place
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
        ok_pick = self.pick_place_mgr.pick(cup_name)
        if not ok_pick:
            return
        self.currently_held_item = cup_name

        ok_place = self.pick_place_mgr.place(cup_name, place_key)
        if ok_place:
            self.currently_held_item = None
   
    def query_llm(self):
        try:
            slot_info = self.slot_info
            system_prompt = (
                "You control a robot that can pick up and place colored cups.\n"
                "When the conversation starts, greet the user with a welcome and give a quick introduction."
                "If the user says anything about stopping or quitting, respond with 'exit'. "
                "The robot can do three separate tasks:\n"
                "  1) pick only\n"
                "  2) place only\n"
                "  3) pick and place\n\n"
                "Available cups: RedCup, GreenCup, BlueCup, YellowCup, PurpleCup.\n"
                "Available places: A, B, C, AA, BB, CC.\n\n"

                "Users may provide one or more instructions in a single sentence, such as:\n"
                "  'Pick up the red cup and place it in AA, then pick up the green cup and put it in BB.'\n"
                "Respond with a step-by-step list, using this exact format:\n"
                "  Step 1: pick RedCup and place in AA\n"
                "  Step 2: pick GreenCup and place in BB\n\n"

                "If the robot is already holding a cup, and the user says to place it, do not add a pick step.\n"
                "If the user only says 'pick up the red cup,' do not add a place step.\n"

                "When the user references a location with a spatial term (e.g. 'to the right of BB'), you can "
                "determine which place key is actually 'to the right' by using the XY coordinate table below.\n"
                "Do not say 'to the right of BB' in your final output. Instead, replace it with the exact place name.\n\n"

                "Here are the XY coordinates of each place:\n"
                f"{slot_info}\n\n"

                "Spatial definitions:\n"
                "- 'Below' => if Y coordinate of place is GREATER than the Y of the reference.\n"
                "- 'Above' => if Y coordinate of place is SMALLER than the Y of the reference.\n"
                "- 'Left' => if X coordinate is GREATER than the reference's X.\n"
                "- 'Right' => if X coordinate is SMALLER than the reference's X.\n"
                "Examples:\n"
                "- If A is (1.42, -0.04) and AA is (1.42, 0.21), then AA is BELOW A.\n"
                "- If BB is (1.13, 0.21) and CC is (0.83, 0.21), then CC is to the RIGHT of BB.\n"
                "- If BB is (1.13, 0.21) and B is (1.13, -0.04), B is ABOVE BB.\n"
                "- If CC is (0.83, 0.21) and BB is (1.13, 0.21), BB is to the LEFT of CC.\n\n"

                "Minor Spelling Mistakes:\n"
                " - If the user spells a color or place name slightly incorrectly but it clearly matches one of the known options, "
                "   please correct it automatically. For example, if user says 'grean cup', interpret that as 'GreenCup'.\n"
                " - If the user's spelling is truly ambiguous or conflicts with more than one known option, ask for clarification.\n\n"
                
                "Formatting Requirements:\n"
                "- ALWAYS respond with step-by-step lines in the format:\n"
                "    Step 1: pick RedCup\n"
                "    Step 2: place in BB\n"
                "or\n"
                "    Step 1: pick RedCup and place in BB\n"
                "- If you have multiple steps, number them in increasing order.\n"
                "- If something is unclear, respond with a single clarifying question.\n"
                
                "You can also respond to general small talk. If the user’s message does not contain any pick/place instructions, "
                "respond politely with a short, casual reply. "
            )
            
            client = OpenAI(api_key="sk-", base_url="https://api.deepseek.com")
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *self.chat_history
                ],
                temperature=0.0
            )
            # resp = openai.chat.completions.create(
            #     # model="gpt-3.5-turbo",
            #     model="gpt-4-turbo",
            #     messages=[
            #         {"role": "system", "content": system_prompt},
            #         *self.chat_history
            #     ],
            #     temperature=0.0
            # )
            return resp.choices[0].message.content

        except Exception as e:
            self.get_logger().error(f"LLM error: {str(e)}")
            return "I'm sorry, something went wrong."


    def extract_color(self, text):
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

def main(args=None):
    rclpy.init(args=args)
    node = LLMNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pick_place_mgr.destroy_node()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()