#!/usr/bin/env python3
import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import PoseStamped, Quaternion
from moveit_msgs.msg import (
    MotionPlanRequest,
    Constraints,
    PositionConstraint,
    OrientationConstraint,
    PlanningOptions
)
from moveit_msgs.action import MoveGroup, ExecuteTrajectory

# dictionary of known object poses:
OBJECT_GOALS = {
    "RedCup": {
        "position": [1.01, 1.295022, 1.27],
        "orientation": [0.720, 0.694, -0.029, -0.013]
    },
    "GreenCup": {
        "position": [1.166, 1.260, 1.408],
        "orientation": [0.752, 0.658, 0.038, -0.018]
    },
    "BlueCup": {
        "position": [1.29, 1.27, 1.27],
        "orientation": [0.714, 0.699, -0.032, -0.041]
    },
    "YellowCup": {
        "position": [0.963062, 1.461358, 1.27],
        "orientation": [0.714, 0.699, -0.032, -0.041]
    },
    "PurpleCup": {
        "position": [1.168, 1.466, 1.27],
        "orientation": [0.714, 0.699, -0.032, -0.041]
    },
}

class PredefinedObjectClient(Node):
    def __init__(self, goal_name):
        super().__init__('predefined_object_client')
        self._move_client = ActionClient(self, MoveGroup, '/move_action')
        self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        self.done = False
        self.goal_name = goal_name

    def send_goal(self):
        self.get_logger().info("Waiting for /move_action server...")
        self._move_client.wait_for_server()
        self.get_logger().info("Waiting for /execute_trajectory server...")
        self._exec_client.wait_for_server()

        # Lookup the goal pose from the dictionary
        if self.goal_name not in OBJECT_GOALS:
            self.get_logger().error(f"Goal '{self.goal_name}' not found in OBJECT_GOALS!")
            self.done = True
            return

        pos = OBJECT_GOALS[self.goal_name]["position"]
        ori = OBJECT_GOALS[self.goal_name]["orientation"]

        # Build the MoveGroup request
        goal_msg = MoveGroup.Goal()
        request = MotionPlanRequest()
        request.group_name = "ur_manipulator"
        request.allowed_planning_time = 5.0
        request.max_velocity_scaling_factor = 0.7
        request.max_acceleration_scaling_factor = 0.7

        # Create a bounding region
        constraints = Constraints()

        pc = PositionConstraint()
        pc.header.frame_id = "world"
        pc.link_name = "tool0"
        pc.weight = 1.0
        # The bounding region --> small sphere around the target
        from shape_msgs.msg import SolidPrimitive
        from geometry_msgs.msg import Pose

        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [0.008]  # 8 mm radius

        sphere_pose = Pose()
        sphere_pose.position.x = pos[0]
        sphere_pose.position.y = pos[1]
        sphere_pose.position.z = pos[2]
        sphere_pose.orientation.w = 1.0

        pc.constraint_region.primitives.append(sphere)
        pc.constraint_region.primitive_poses.append(sphere_pose)

        oc = OrientationConstraint()
        oc.header.frame_id = "world"
        oc.link_name = pc.link_name
        oc.weight = 1.0
        oc.orientation.x = ori[0]
        oc.orientation.y = ori[1]
        oc.orientation.z = ori[2]
        oc.orientation.w = ori[3]
        # orientation tolerance
        oc.absolute_x_axis_tolerance = 0.1
        oc.absolute_y_axis_tolerance = 0.1
        oc.absolute_z_axis_tolerance = 0.1

        constraints.position_constraints.append(pc)
        constraints.orientation_constraints.append(oc)
        request.goal_constraints.append(constraints)

        # Minimal planning options
        planning_options = PlanningOptions()
        planning_options.planning_scene_diff.is_diff = True
        planning_options.planning_scene_diff.robot_state.is_diff = True

        goal_msg.request = request
        goal_msg.planning_options = planning_options

        # Send the request
        self.get_logger().info(f"Sending MoveIt goal for object: {self.goal_name}")
        future = self._move_client.send_goal_async(goal_msg, feedback_callback=self.feedback_cb)
        future.add_done_callback(self.goal_response_cb)

    def feedback_cb(self, feedback):
        self.get_logger().info(f"Feedback: {feedback.feedback}")

    def goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal was rejected by MoveGroup.")
            self.done = True
            return

        self.get_logger().info("Goal accepted. Waiting for result...")
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_cb)

    def result_cb(self, future):
        result = future.result().result
        if result.error_code.val == 1:
            self.get_logger().info("Motion planning + execution succeeded!")
        else:
            self.get_logger().error(f"Motion failed with error code: {result.error_code.val}")
        self.done = True

def main(args=None):
    rclpy.init(args=args)

    goal_name = "GreenCup"  # default
    for arg in sys.argv:
        if "goal:=" in arg:
            goal_name = arg.split(":=")[1]

    node = PredefinedObjectClient(goal_name)
    node.send_goal()

    while rclpy.ok() and not node.done:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
