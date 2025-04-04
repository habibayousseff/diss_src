#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import GripperCommand

class GripperCommander(Node):
    def __init__(self, server_name='gripper_controller/gripper_cmd'):
        super().__init__('gripper_commander')

        # Create an action client for the GripperCommand action
        self.client = ActionClient(self, GripperCommand, server_name)
        self.get_logger().info(f"Waiting for GripperCommand action server on {server_name}...")
        self.client.wait_for_server()
        self.get_logger().info("Connected to GripperCommand action server.")

    def send_goal(self, position, max_effort=100.0):
        goal_msg = GripperCommand.Goal()
        goal_msg.command.position = position
        goal_msg.command.max_effort = max_effort

        self.get_logger().info(f"Sending goal: position={position:.3f} m, max_effort={max_effort}")
        send_goal_future = self.client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal Rejected!")
            return

        self.get_logger().info("Goal Accepted!")
        get_result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, get_result_future)
        result = get_result_future.result().result
        self.get_logger().info(f"Gripper action result: reached_goal={result.reached_goal}, stalled={result.stalled}")

def main(args=None):
    rclpy.init(args=args)
    node = GripperCommander(server_name='gripper_controller/gripper_cmd')

    # Example usage:
    # node.send_goal(position=0.004)  # "open"
    # node.get_logger().info("Opened the gripper")
    
    node.send_goal(position=0.06)   # "middle"
    node.get_logger().info("Moved to middle")
    
    node.send_goal(position=0.004)  # "open"
    node.get_logger().info("Opened the gripper")
    
    node.send_goal(position=0.085)  # "close"
    node.get_logger().info("Closed the gripper")

    rclpy.shutdown()

if __name__ == '__main__':
    main()
