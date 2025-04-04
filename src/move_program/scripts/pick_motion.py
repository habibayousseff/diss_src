#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool
from moveit_msgs.srv import AttachObject, DetachObject

class PickMotion(Node):
    def __init__(self):
        super().__init__('pick_motion')
        
        # Service to toggle grasping
        self.srv = self.create_service(
            SetBool, 'pick_up', self.pick_callback)
            
        # MoveIt attach/detach clients
        self.attach_client = self.create_client(
            AttachObject, '/attach_object')
        self.detach_client = self.create_client(
            DetachObject, '/detach_object')
            
        self.object_name = "target_object"  # Name of your cup object

    def pick_callback(self, request, response):
        if request.data:  # Grasp command
            req = AttachObject.Request()
            req.object_name = self.object_name
            req.link_name = "tool0"  # EE link
            req.touch_links = ["wrist_3_link"]  # Allow contact with arm
            
            future = self.attach_client.call_async(req)
            response.success = True
        else:  # Release command
            req = DetachObject.Request()
            req.object_name = self.object_name
            
            future = self.detach_client.call_async(req)
            response.success = True
            
        return response

def main(args=None):
    rclpy.init(args=args)
    node = PickMotion()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()