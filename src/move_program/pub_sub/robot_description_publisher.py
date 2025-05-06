#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class RobotDescriptionPublisher(Node):
    def __init__(self):
        super().__init__('robot_description_publisher')
        # Declare the 'robot_description' parameter.
        self.declare_parameter('robot_description', '')
        # Publisher on topic '/robot_description_topic'
        qos_profile = rclpy.qos.QoSProfile(depth=1)
        self.publisher_ = self.create_publisher(String, 'robot_description_topic', qos_profile)
        # Publish every 1 second.
        self.create_timer(1.0, self.publish_robot_description)

    def publish_robot_description(self):
        robot_description = self.get_parameter('robot_description').get_parameter_value().string_value
        if robot_description:
            msg = String()
            msg.data = robot_description
            self.publisher_.publish(msg)
        else:
            self.get_logger().warn('robot_description parameter is empty.')

def main(args=None):
    rclpy.init(args=args)
    node = RobotDescriptionPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
