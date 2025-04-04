#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json

class ParameterPublisher(Node):
    def __init__(self):
        super().__init__('parameter_publisher')
        # Declare the parameters you want to share.
        # In your launch file you can set these parameters.
        self.declare_parameter('robot_description', '')
        self.declare_parameter('robot_description_semantic', '')
        self.declare_parameter('kinematics_parameters', '')  # For example
        
        # Create a publisher with a transient local QoS so late subscribers get the message.
        qos_profile = rclpy.qos.QoSProfile(
            depth=1,
            reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
            durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL
        )
        self.publisher_ = self.create_publisher(String, 'robot_parameters', qos_profile)
        # Use a timer to publish the parameters once (or periodically, if desired).
        self.create_timer(1.0, self.publish_parameters)

    def publish_parameters(self):
        # Get parameters from this node's parameter server.
        rd = self.get_parameter('robot_description').get_parameter_value().string_value
        rds = self.get_parameter('robot_description_semantic').get_parameter_value().string_value
        kin = self.get_parameter('kinematics_parameters').get_parameter_value().string_value
        # Build a dictionary of parameters.
        param_dict = {
            'robot_description': rd,
            'robot_description_semantic': rds,
            'kinematics_parameters': kin,
        }
        msg = String()
        msg.data = json.dumps(param_dict)
        self.publisher_.publish(msg)
        self.get_logger().info('Published robot parameters.')

def main(args=None):
    rclpy.init(args=args)
    node = ParameterPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
