#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class SrdfPublisher(Node):
    def __init__(self):
        super().__init__('srdf_publisher')
        # Declare and get the parameter robot_description_semantic.
        self.declare_parameter('robot_description_semantic', '')
        # Create a publisher on the topic "robot_description_semantic" with transient_local QoS.
        qos_profile = rclpy.qos.QoSProfile(
            depth=1,
            reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
            durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL
        )
        self.publisher_ = self.create_publisher(String, 'robot_description_semantic', qos_profile)
        # Publish immediately (and you could also set up a timer for periodic updates if needed).
        self.publish_srdf()

    def publish_srdf(self):
        srdf = self.get_parameter('robot_description_semantic').get_parameter_value().string_value
        if srdf:
            msg = String()
            msg.data = srdf
            self.publisher_.publish(msg)
            self.get_logger().info('Published robot_description_semantic')
        else:
            self.get_logger().warn('robot_description_semantic is empty.')

def main(args=None):
    rclpy.init(args=args)
    node = SrdfPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
