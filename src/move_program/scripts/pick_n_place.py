#!/usr/bin/env python3
import sys
import time  # For debug delays
import threading

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from builtin_interfaces.msg import Duration
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


################################################################################
# We store just the FINAL pick pose for "GreenCup" and the place pose.
################################################################################
OBJECT_GOALS = {
    "RedCup": {
        "position": [0.9226, 1.2018, 1.368],  # Final pick
        "orientation": [0.739, 0.673, 0.014, -0.023],
    },
    "GreenCup": {
        "position": [1.184, 1.281, 1.384],  # Final pick
        "orientation": [0.739, 0.673, 0.014, -0.023],
    },
    "BlueCup": {
        "position": [1.46, 1.203, 1.368],  # Final pick
        "orientation": [0.739, 0.673, 0.014, -0.023],
    },
    "YellowCup": {
        "position": [0.99, 1.427, 1.368],  # Final pick
        "orientation": [0.739, 0.673, 0.014, -0.023],
    },
    "PurpleCup": {
        "position": [1.385, 1.393, 1.368],  # Final pick
        "orientation": [0.739, 0.673, 0.014, -0.023],
    },
}

PLACE_GOAL = {
    "PlaceGoal": {
        "position": [1.154, 0.249, 1.293],
        "orientation": [-0.041, 0.999, -0.002, -0.006]
    },
    "TestConfig": {
        "position": [1.154, 0.288, 1.604],
        "orientation": [-0.040, 0.996, 0.076, -0.009]
    },
}
################################################################################
# Gripper positions
################################################################################
GRIPPER_OPEN  = 0.004
GRIPPER_CLOSE = 0.08
GRIPPER_MIDDLE = 0.06

class PickAndPlaceObject(Node):
    def __init__(self, goal_name):
        super().__init__('pick_and_place_object_node')
        self._goal_name = goal_name

        # Action servers
        self._move_client = ActionClient(self, MoveGroup, '/move_action')
        self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        self._gripper_client = ActionClient(self, GripperCommand, 'gripper_controller/gripper_cmd')

        self._done = False

    def send_pick_and_place(self):
        # 1) Wait for servers
        self.get_logger().info("Waiting for /move_action server...")
        self._move_client.wait_for_server()

        self.get_logger().info("Waiting for /execute_trajectory server...")
        self._exec_client.wait_for_server()

        self.get_logger().info("Waiting for gripper_controller/gripper_cmd server...\n")
        self._gripper_client.wait_for_server()

        # 2) Validate pick pose
        if self._goal_name not in OBJECT_GOALS:
            self.get_logger().error(f"Goal '{self._goal_name}' not found in OBJECT_GOALS!")
            self._done = True
            return

        pick_data = OBJECT_GOALS[self._goal_name]
        pick_pos = pick_data["position"]
        pick_orient = pick_data["orientation"]

        # Step 1: open the gripper
        self.open_gripper()
        time.sleep(2)  # debug delay

        # Just add 0.09 to the final pick's z coordinate
        approach_pos = pick_pos.copy()
        approach_pos[2] += 0.097

        # Step 2A: move down to final pick pose
        self.get_logger().info("Lowering to final pick pose.")
        ok_final = self.move_ee_to_pose(
            approach_pos, pick_orient, sphere_radius=0.01
        )
        if not ok_final:
            self.get_logger().error("Pick motion plan failed. Aborting.")
            self._done = True
            return
        time.sleep(2)
        
        # Step 2B: approach offset pose (9 cm above final pick)
        self.get_logger().info("Moving above the object (offset approach).")
        ok_approach = self.move_ee_to_pose(
            pick_pos, pick_orient, sphere_radius=0.01
        )
        if not ok_approach:
            self.get_logger().error("Approach motion failed. Aborting entire sequence.")
            self._done = True
            return
        time.sleep(2)
        
        
        # Step 3: close the gripper (simulate grasp)
        self.close_gripper()
        time.sleep(2)
        
        self.get_logger().info("Moving above the object (offset approach).")
        ok_approach = self.move_ee_to_pose(
            approach_pos, pick_orient, sphere_radius=0.01
        )
        
        # Step 4: move to place pose
        place_1_success = self.move_ee_to_pose(
            PLACE_GOAL["TestConfig"]["position"],
            PLACE_GOAL["TestConfig"]["orientation"],
            sphere_radius=0.01
        )
        if not place_1_success:
            self.get_logger().error("Place motion plan failed. Aborting.")
            self._done = True
            return
        time.sleep(2)
        
        # Step 4: move to place pose
        place_2_success = self.move_ee_to_pose(
            PLACE_GOAL["PlaceGoal"]["position"],
            PLACE_GOAL["PlaceGoal"]["orientation"],
            sphere_radius=0.01
        )
        if not place_2_success:
            self.get_logger().error("Place motion plan failed. Aborting.")
            self._done = True
            return
        time.sleep(2)

        # Step 5: open the gripper to release
        self.open_gripper()
        time.sleep(2)

        self.get_logger().info("Pick and place sequence finished.\n")
        self._done = True

    ############################################################################
    # Gripper Commands
    ############################################################################

    def open_gripper(self):
        self.set_gripper_position(GRIPPER_OPEN, max_effort=100.0)
        self.get_logger().info("Gripper opened.\n")

    def close_gripper(self):
        def blocking_gripper_call():
            self.set_gripper_position(GRIPPER_CLOSE, max_effort=100.0)

        gripper_thread = threading.Thread(target=blocking_gripper_call)
        gripper_thread.start()
        gripper_thread.join(timeout=2.0)  # wait max 2 seconds

        if gripper_thread.is_alive():
            self.get_logger().warn("Gripper took too long — continuing anyway.")
        else:
            self.get_logger().info("Gripper closed (or finished early).")
        # self.set_gripper_position(GRIPPER_CLOSE, max_effort=100.0)
        # self.get_logger().info("Gripper closed.\n")

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

        get_result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, get_result_future)
        if get_result_future.result():
            result = get_result_future.result().result
            self.get_logger().info(
                f"Gripper result: reached_goal={result.reached_goal}, stalled={result.stalled}"
            )

    ############################################################################
    # Move End-Effector to a Pose
    ############################################################################
    def move_ee_to_pose(self, position, orientation, sphere_radius=0.01):
        """
        Creates a bounding sphere around the target (x, y, z) + orientation for 'tool0'
        and sends a goal to MoveGroup. Returns True if plan+execution succeeded.
        """
        goal_msg = MoveGroup.Goal()

        request = MotionPlanRequest()
        request.group_name = "ur_manipulator"
        request.allowed_planning_time = 10.0  # Increased from 5.0 to reduce timeouts
        request.max_velocity_scaling_factor = 0.7
        request.max_acceleration_scaling_factor = 0.7

        constraints = Constraints()

        # PositionConstraint
        pc = PositionConstraint()
        pc.header.frame_id = "world"
        pc.link_name = "tool0"
        pc.weight = 1.0

        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [sphere_radius]

        sphere_pose = Pose()
        sphere_pose.position.x = position[0]  # x
        sphere_pose.position.y = position[1]  # y
        sphere_pose.position.z = position[2]  # z
        sphere_pose.orientation.w = 1.0

        pc.constraint_region.primitives.append(sphere)
        pc.constraint_region.primitive_poses.append(sphere_pose)

        # OrientationConstraint
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

        constraints.position_constraints.append(pc)
        constraints.orientation_constraints.append(oc)
        request.goal_constraints.append(constraints)

        planning_options = PlanningOptions()
        planning_options.planning_scene_diff.is_diff = True
        planning_options.planning_scene_diff.robot_state.is_diff = True

        goal_msg.request = request
        goal_msg.planning_options = planning_options

        self.get_logger().info(
            f"Sending MoveIt goal near: ({position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f})"
        )
        future = self._move_client.send_goal_async(goal_msg, feedback_callback=self.feedback_cb)
        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()
        if not goal_handle or not goal_handle.accepted:
            self.get_logger().error("Goal was rejected by MoveGroup.")
            return False

        self.get_logger().info("Goal accepted. Waiting for result...")
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result_msg = result_future.result()
        if not result_msg:
            self.get_logger().error("No result message from MoveGroup.")
            return False

        result = result_msg.result
        if result.error_code.val == 1:
            self.get_logger().info("Motion plan + execution succeeded!\n")
            return True
        else:
            self.get_logger().error(f"Motion failed with error code: {result.error_code.val}\n")
            return False

    def feedback_cb(self, feedback):
        # If you want to process feedback, do so here
        self.get_logger().debug(f"Feedback: {feedback.feedback}")

def main(args=None):
    rclpy.init(args=args)

    # Default pick is "GreenCup"
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