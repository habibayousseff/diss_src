#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

# ROS / MoveIt messages
from geometry_msgs.msg import PoseStamped, Pose
from shape_msgs.msg import SolidPrimitive
from moveit_msgs.msg import (
    MotionPlanRequest,
    PlanningOptions,
    Constraints,
    PositionConstraint,
    OrientationConstraint
)
from moveit_msgs.action import MoveGroup, ExecuteTrajectory

class PoseGoalClient(Node):
    def __init__(self):
        super().__init__('pose_goal_with_orientation')
        self._move_client = ActionClient(self, MoveGroup, '/move_action')
        self._exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        self.done = False

    def send_goal(self):
        # 1) Wait for the MoveGroup + ExecuteTrajectory servers
        self.get_logger().info("Waiting for /move_action server...")
        self._move_client.wait_for_server()
        self.get_logger().info("Waiting for /execute_trajectory server...")
        self._exec_client.wait_for_server()

        # 2) Build the MotionPlanRequest
        goal_msg = MoveGroup.Goal()
        request = MotionPlanRequest()
        request.group_name = "ur_manipulator"

        # Use slower speeds to reduce overshoot in Gazebo
        request.max_velocity_scaling_factor = 0.7
        request.max_acceleration_scaling_factor = 0.7

        # Give the planner more time
        request.allowed_planning_time = 5.0

        # 3) Define the target pose
        pose_goal = PoseStamped()
        pose_goal.header.frame_id = "world"
        pose_goal.pose.position.x = 1.142
        pose_goal.pose.position.y = 0.283
        pose_goal.pose.position.z = 1.618
        pose_goal.pose.orientation.x = -0.021
        pose_goal.pose.orientation.y =  0.998
        pose_goal.pose.orientation.z =  0.056
        pose_goal.pose.orientation.w =  0.009

        # 4) Create position + orientation constraints
        constraints = Constraints()

        # ------------------ Position Constraint ------------------
        pc = PositionConstraint()
        pc.header = pose_goal.header
        pc.link_name = "tool0" 
        pc.weight = 1.0

        # A small bounding sphere around the desired position
        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [0.001]  # 1 mm

        sphere_pose = Pose()
        sphere_pose.position = pose_goal.pose.position
        sphere_pose.orientation.w = 1.0 
        pc.constraint_region.primitives.append(sphere)
        pc.constraint_region.primitive_poses.append(sphere_pose)

        # ---------------- Orientation Constraint ----------------
        oc = OrientationConstraint()
        oc.header = pose_goal.header
        oc.link_name = pc.link_name
        oc.orientation = pose_goal.pose.orientation
        oc.absolute_x_axis_tolerance = 0.05
        oc.absolute_y_axis_tolerance = 0.05
        oc.absolute_z_axis_tolerance = 0.05
        oc.weight = 1.0

        constraints.position_constraints.append(pc)
        constraints.orientation_constraints.append(oc)
        request.goal_constraints.append(constraints)

        # 5) Minimal planning options
        planning_options = PlanningOptions()
        planning_options.planning_scene_diff.is_diff = True
        planning_options.planning_scene_diff.robot_state.is_diff = True

        goal_msg.request = request
        goal_msg.planning_options = planning_options

        # 6) Send the goal
        self.get_logger().info("Sending position + orientation goal to MoveGroup...")
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
            self.get_logger().error(f"Motion planning failed with error code: {result.error_code.val}")
        self.done = True

class ConditionalNode(Node):
    def __init__(self):
        super().__init__('conditional_node')
        self.get_logger().info("Press 'x' to send the pose+orientation goal. Anything else to skip.")

    def run(self):
        key = input("Your input: ")
        if key.lower() == 'x':
            client = PoseGoalClient()
            client.send_goal()
            while rclpy.ok() and not client.done:
                rclpy.spin_once(client, timeout_sec=0.1)
            client.destroy_node()
        else:
            self.get_logger().info("Skipping motion plan")

def main(args=None):
    rclpy.init(args=args)
    node = ConditionalNode()
    node.run()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
