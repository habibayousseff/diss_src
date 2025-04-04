#!/usr/bin/env python3
"""
ee_pos.py

This node subscribes to TF transforms and prints the end-effector (wrist_3_link)
position continuously.
"""

import rclpy
from rclpy.node import Node
import tf2_ros
from geometry_msgs.msg import TransformStamped

class EndEffectorPosition(Node):
    def __init__(self):
        super().__init__('end_effector_position')
        # Create a TF2 buffer and listener
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        # Create a timer to query the transform every 1 second.
        self.create_timer(1.0, self.print_ee_position)

    def print_ee_position(self):
        try:
            # Query the transform from base (or world) to end-effector
            trans: TransformStamped = self.tf_buffer.lookup_transform(
                'world',             # target frame (adjust as needed)
                'tool0',      # source frame (end-effector)
                rclpy.time.Time(),   # latest available transform
                timeout=rclpy.duration.Duration(seconds=1.0)
            )
            pos = trans.transform.translation
            self.get_logger().info(f"EE Position - x: {pos.x:.3f}, y: {pos.y:.3f}, z: {pos.z:.3f}")
            rot = trans.transform.rotation
            self.get_logger().info(f"EE Orientation - x: {rot.x:.3f}, y: {rot.y:.3f}, z: {rot.z:.3f}, w: {rot.w:.3f}")

        except Exception as e:
            self.get_logger().warn(f"Could not get transform: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = EndEffectorPosition()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
