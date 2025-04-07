#!/usr/bin/env python3
import sys
import time
import threading

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from builtin_interfaces.msg import Duration
from visualization_msgs.msg import Marker
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
    "Up": {
        "position": [1.061, 0.542, 2.101],
        "orientation": [0.000, 0.707, 0.707, -0.000]
    },
    "A": {
        "position": [1.42, -0.042, 1.1923],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "B": {
        "position": [1.113, -0.037, 1.1923],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "C": {
        "position": [0.839, -0.0514, 1.1923],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "AA": {
        "position": [1.43, 0.215, 1.1923],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "BB": {
        "position": [1.131, 0.22, 1.1923],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "CC": {
        "position": [0.83, 0.21, 1.1923],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    
}

GRIPPER_OPEN  = 0.004
GRIPPER_CLOSE = 0.08
GRIPPER_MIDDLE = 0.06

class PickAndPlaceObject(Node):
    def __init__(self, goal_name):
        super().__init__('pick_and_place_object_node')
        self._goal_name = goal_name

        self._move_client = ActionClient(self, MoveGroup, '/move_action')
        self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        self._gripper_client = ActionClient(self, GripperCommand, 'gripper_controller/gripper_cmd')
        self._done = False

    def send_pick_and_place(self):
        self.get_logger().info("Waiting for action servers...")
        self._move_client.wait_for_server()
        self._exec_client.wait_for_server()
        self._gripper_client.wait_for_server()

        if self._goal_name not in OBJECT_GOALS:
            self.get_logger().error(f"Goal '{self._goal_name}' not found in OBJECT_GOALS!")
            self._done = True
            return

        pick_data = OBJECT_GOALS[self._goal_name]
        pick_pos = pick_data["position"]
        pick_orient = pick_data["orientation"]

        self.open_gripper()
        time.sleep(2)

        approach_pos_pick = pick_pos.copy()
        approach_pos_pick[2] += 0.097

        self.get_logger().info("1. Move above object (approach pose).")
        if not self.move_ee_to_pose(approach_pos_pick, pick_orient, max_attempts=25):
            self.abort("Approach motion plan failed.")
            return
        time.sleep(2)

        self.get_logger().info("2. Move down to final pick pose.")
        if not self.move_ee_to_pose(pick_pos, pick_orient, max_attempts=25):
            self.abort("Pick pose motion failed.")
            return
        time.sleep(2)

        self.get_logger().info("3. Close gripper to grasp.")
        self.close_gripper()
        time.sleep(2)

        self.get_logger().info("4. Lift object to approach pose.")
        if not self.move_ee_to_pose(approach_pos_pick, pick_orient, max_attempts=25):
            self.abort("Lift motion failed.")
            return
        time.sleep(2)

        self.get_logger().info("5. Move to intermediate place pose (TestConfig).")
        place_test = PLACE_GOAL["TestConfig"]
        if not self.move_ee_to_pose(place_test["position"], place_test["orientation"], max_attempts=25):
            self.abort("TestConfig place pose failed.")
            return
        time.sleep(2)

        self.get_logger().info("6. Move to final place pose (TrialPlaceGoal).")
        place_final = PLACE_GOAL["TrialPlaceGoal"]
        if not self.move_ee_to_pose(place_final["position"], place_final["orientation"], max_attempts=25):
            self.abort("Final place pose failed.")
            return
        time.sleep(2)

        self.get_logger().info("7. Open gripper to release.")
        self.mid_gripper()
        time.sleep(2)
        
        self.get_logger().info("8. Move to intermediate place pose (TestConfig).")
        place_test = PLACE_GOAL["TestConfig"]
        if not self.move_ee_to_pose(place_test["position"], place_test["orientation"], max_attempts=25):
            self.abort("TestConfig place pose failed.")
            return
        time.sleep(2)
        
        self.get_logger().info("9. Move to start position.")
        place_test = PLACE_GOAL["Up"]
        if not self.move_ee_to_pose(place_test["position"], place_test["orientation"], max_attempts=25):
            self.abort("Start position place pose failed.")
            return
        time.sleep(2)

        self.get_logger().info("Pick and place sequence complete ✅")
        self._done = True

    def abort(self, message):
        self.get_logger().error(message + " Aborting sequence.")
        self._done = True

    def open_gripper(self):
        self.set_gripper_position(GRIPPER_OPEN, max_effort=100.0)
        self.get_logger().info("Gripper opened.\n")
    
    def mid_gripper(self):
        self.set_gripper_position(GRIPPER_MIDDLE, max_effort=100.0)
        self.get_logger().info("Gripper opened.\n")

    def close_gripper(self):
        goal_msg = GripperCommand.Goal()
        goal_msg.command.position = GRIPPER_CLOSE
        goal_msg.command.max_effort = 100.0

        self.get_logger().info(f"Sending GripperCommand: pos={GRIPPER_CLOSE:.3f}, effort=100.0")
        send_goal_future = self._gripper_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()

        if not goal_handle or not goal_handle.accepted:
            self.get_logger().error("Gripper command rejected!")
            return

        start_time = time.time()
        timeout = 60  # seconds

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

        time.sleep(2)  # Still useful for stability

    def set_gripper_position(self, position, max_effort=100.0):
        goal_msg = GripperCommand.Goal()
        goal_msg.command.position = position
        goal_msg.command.max_effort = max_effort

        self.get_logger().info(f"Sending GripperCommand: pos={position:.3f}, effort={max_effort}")
        send_goal_future = self._gripper_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()
        if not goal_handle or not goal_handle.accepted:
            self.get_logger().error("Gripper command rejected!")
            return

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result().result
        self.get_logger().info(f"Gripper result: reached_goal={result.reached_goal}, stalled={result.stalled}")

    def move_ee_to_pose(self, position, orientation, sphere_radius=0.01, max_attempts=25):
        goal_msg = MoveGroup.Goal()

        request = MotionPlanRequest()
        request.group_name = "ur_manipulator"
        request.allowed_planning_time = 10.0
        request.max_velocity_scaling_factor = 0.7
        request.max_acceleration_scaling_factor = 0.7

        constraints = Constraints()

        # === PositionConstraint for tool0 (target pose) ===
        pc = PositionConstraint()
        pc.header.frame_id = "world"
        pc.link_name = "tool0"
        pc.weight = 1.0

        target_sphere = SolidPrimitive()
        target_sphere.type = SolidPrimitive.SPHERE
        target_sphere.dimensions = [sphere_radius]

        target_pose = Pose()
        target_pose.position.x = position[0]
        target_pose.position.y = position[1]
        target_pose.position.z = position[2]
        target_pose.orientation.w = 1.0

        pc.constraint_region.primitives.append(target_sphere)
        pc.constraint_region.primitive_poses.append(target_pose)
        constraints.position_constraints.append(pc)

        # === NEW: Z constraint for upper_arm_link (Z between 1.25 and 3.0) ===
        arm_constraint = PositionConstraint()
        arm_constraint.header.frame_id = "world"
        arm_constraint.link_name = "forearm_link"
        arm_constraint.weight = 1.0

        z_box = SolidPrimitive()
        z_box.type = SolidPrimitive.BOX
        z_box.dimensions = [10.0, 10.0, 1.75]  # X, Y, Z size (large XY, Z from 1.25 to 3.0)

        z_box_pose = Pose()
        z_box_pose.position.x = 0.0
        z_box_pose.position.y = 0.0
        z_box_pose.position.z = 2.125  # Center of box = 1.25 + 1.75 / 2
        z_box_pose.orientation.w = 1.0

        arm_constraint.constraint_region.primitives.append(z_box)
        arm_constraint.constraint_region.primitive_poses.append(z_box_pose)
        constraints.position_constraints.append(arm_constraint)

        # === OrientationConstraint for tool0 ===
        oc = OrientationConstraint()
        oc.header.frame_id = "world"
        oc.link_name = pc.link_name
        oc.weight = 1.0
        oc.orientation.x = orientation[0]
        oc.orientation.y = orientation[1]
        oc.orientation.z = orientation[2]
        oc.orientation.w = orientation[3]
        oc.absolute_x_axis_tolerance = 0.1
        oc.absolute_y_axis_tolerance = 0.1
        oc.absolute_z_axis_tolerance = 0.1

        constraints.orientation_constraints.append(oc)
        request.goal_constraints.append(constraints)

        planning_options = PlanningOptions()
        planning_options.planning_scene_diff.is_diff = True
        planning_options.planning_scene_diff.robot_state.is_diff = True

        goal_msg.request = request
        goal_msg.planning_options = planning_options

        attempt = 0
        while attempt < max_attempts:
            self.get_logger().info(
                f"Attempt {attempt + 1} of {max_attempts}: Planning to ({position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f})"
            )

            future = self._move_client.send_goal_async(goal_msg, feedback_callback=self.feedback_cb)
            rclpy.spin_until_future_complete(self, future)
            goal_handle = future.result()

            if not goal_handle or not goal_handle.accepted:
                self.get_logger().warn("Goal was rejected by MoveGroup.")
                attempt += 1
                time.sleep(0.5)
                continue

            self.get_logger().info("Goal accepted. Waiting for result...")
            result_future = goal_handle.get_result_async()
            rclpy.spin_until_future_complete(self, result_future)
            result_msg = result_future.result()

            if result_msg and result_msg.result.error_code.val == 1:
                self.get_logger().info("Motion plan + execution succeeded!\n")
                return True
            else:
                self.get_logger().warn(
                    f"Motion failed with error code: {result_msg.result.error_code.val if result_msg else 'No result'}"
                )
                attempt += 1
                time.sleep(0.5)

        self.get_logger().error("All planning attempts failed.\n")
        return False


    def feedback_cb(self, feedback):
        self.get_logger().debug(f"Feedback: {feedback.feedback}")

def main(args=None):
    rclpy.init(args=args)

    goal_name = "RedCup"
    for arg in sys.argv:
        if "goal:=" in arg:
            goal_name = arg.split(":=")[1]

    node = PickAndPlaceObject(goal_name)
    node.send_pick_and_place()

    while rclpy.ok() and not node._done:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
