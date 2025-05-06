#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import time

# MoveIt / ROS msgs
from moveit_msgs.action import MoveGroup, ExecuteTrajectory
from moveit_msgs.msg import (
    MotionPlanRequest,
    Constraints,
    PositionConstraint,
    OrientationConstraint,
    PlanningOptions,
    PlanningScene,
    CollisionObject,
    AttachedCollisionObject
)
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose

# Simple helper
def moveit_error_string(code):
    error_map = {
        1: "SUCCESS",
        -1: "FAILURE",
        -2: "PLANNING_FAILED",
        -3: "INVALID_MOTION_PLAN",
        -4: "MOTION_PLAN_INVALIDATED_BY_ENVIRONMENT_CHANGE",
        -5: "CONTROL_FAILED",
        -6: "UNABLE_TO_AQUIRE_SENSOR_DATA",
        -7: "TIMED_OUT",
        -10: "START_STATE_IN_COLLISION",
        -11: "START_STATE_VIOLATES_PATH_CONSTRAINTS",
    }
    return error_map.get(code, "UNKNOWN")

class AttachExampleNode(Node):
    def __init__(self):
        super().__init__('attach_example_node')
        self.scene_pub = self.create_publisher(PlanningScene, '/planning_scene', 10)

        # Action clients to MoveIt
        self.move_client = ActionClient(self, MoveGroup, '/move_action')
        self.exec_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')

        self.move_client.wait_for_server()
        self.exec_client.wait_for_server()
        self.get_logger().info("MoveIt servers are ready.")

    # --------------------------------------------------------------------------
    # 1) ADD OBJECT
    # --------------------------------------------------------------------------
    def add_collision_object(self, object_id="my_cylinder", frame_id="world"):
        """
        Adds a cylinder collision object at a chosen position in front of the robot.
        Adjust the pose to match your real scenario.
        """
        # Create a CollisionObject
        co = CollisionObject()
        co.id = object_id
        co.header.frame_id = frame_id
        co.operation = CollisionObject.ADD

        # Define shape (cylinder)
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.CYLINDER  # 2 => cylinder
        primitive.dimensions = [0.15, 0.03]  # [HEIGHT, RADIUS]

        # Pose where we want the cylinder
        cylinder_pose = Pose()
        # For example: a bit in front of the robot on the table
        cylinder_pose.position.x = 0.6
        cylinder_pose.position.y = 0.0
        cylinder_pose.position.z = 0.8
        cylinder_pose.orientation.w = 1.0

        co.primitives.append(primitive)
        co.primitive_poses.append(cylinder_pose)

        # Put it into a PlanningScene
        scene_msg = PlanningScene()
        scene_msg.is_diff = True
        scene_msg.world.collision_objects.append(co)

        # Publish
        self.scene_pub.publish(scene_msg)
        rclpy.spin_once(self)
        time.sleep(1.0)
        self.get_logger().info(f"Added collision object '{object_id}'")

    # --------------------------------------------------------------------------
    # 2) ATTACH
    # --------------------------------------------------------------------------
    def attach_object(self, object_id="my_cylinder", link_name="gripper_base"):
        """
        Attach an existing collision object to a link so that it moves with the robot.
        """
        aco = AttachedCollisionObject()
        aco.link_name = link_name
        aco.object.id = object_id
        aco.object.operation = CollisionObject.ADD
        # aco.object.is_attached = True
        aco.object.header.frame_id = link_name

        # Must match the same shape as originally added
        prim = SolidPrimitive()
        prim.type = SolidPrimitive.CYLINDER
        prim.dimensions = [0.15, 0.03]
        aco.object.primitives.append(prim)

        # Relative pose on the link
        link_pose = Pose()
        link_pose.position.z = 0.2 # or 0.05 if you want it above the link
        link_pose.orientation.w = 1.0
        aco.object.primitive_poses.append(link_pose)

        scene_msg = PlanningScene()
        scene_msg.is_diff = True
        scene_msg.robot_state.attached_collision_objects.append(aco)

        self.scene_pub.publish(scene_msg)
        rclpy.spin_once(self)
        time.sleep(1.0)
        self.get_logger().info(f"Attached '{object_id}' to link '{link_name}'")

    # --------------------------------------------------------------------------
    # 3) DETACH
    # --------------------------------------------------------------------------
    def detach_object(self, object_id="my_cylinder", link_name="gripper_base"):
        """
        Detach from link and leave object in the scene (if you want).
        """
        aco = AttachedCollisionObject()
        aco.link_name = link_name
        aco.object.id = object_id
        aco.object.header.frame_id = link_name
        aco.object.operation = CollisionObject.REMOVE  # <- THIS is key

        scene_msg = PlanningScene()
        scene_msg.is_diff = True
        scene_msg.robot_state.attached_collision_objects.append(aco)
        scene_msg.robot_state.is_diff = True
        
        self.scene_pub.publish(scene_msg)
        rclpy.spin_once(self)
        time.sleep(1.0)
        self.get_logger().info(f"Detached '{object_id}' from '{link_name}'")
        
    # --------------------------------------------------------------------------
    # 4) REMOVE
    # --------------------------------------------------------------------------
    def remove_object(self, object_id="my_cylinder"):
        """
        Remove the object from the scene entirely.
        """
        co = CollisionObject()
        co.id = object_id
        co.header.frame_id = "world"
        co.operation = CollisionObject.REMOVE

        scene_msg = PlanningScene()
        scene_msg.is_diff = True
        scene_msg.world.collision_objects.append(co)

        self.scene_pub.publish(scene_msg)
        rclpy.spin_once(self)
        time.sleep(1.0)
        self.get_logger().info(f"Removed collision object '{object_id}'")

    # --------------------------------------------------------------------------
    # EXAMPLE MOTION
    # --------------------------------------------------------------------------
    def move_ee_to_pose(self, x, y, z, max_attempts=10):
        """
        Plans + executes a very simple position constraint (with orientation w=1).
        Just to see the robot move near the object.
        """
        from moveit_msgs.msg import MoveItErrorCodes

        for attempt in range(max_attempts):
            self.get_logger().info(f"Attempt {attempt+1}/{max_attempts} to move to x={x:.3f}, y={y:.3f}, z={z:.3f}")

            # Build a MoveGroup goal
            goal = MoveGroup.Goal()
            request = MotionPlanRequest()
            request.group_name = "ur_manipulator"
            request.allowed_planning_time = 5.0

            # Position constraint
            c = Constraints()
            pc = PositionConstraint()
            pc.header.frame_id = "world"
            pc.link_name = "tool0"
            pc.weight = 1.0

            sphere = SolidPrimitive()
            sphere.type = SolidPrimitive.SPHERE
            sphere.dimensions = [0.02]  # 2cm radius bound
            sphere_pose = Pose()
            sphere_pose.position.x = x
            sphere_pose.position.y = y
            sphere_pose.position.z = z
            sphere_pose.orientation.w = 1.0

            pc.constraint_region.primitives.append(sphere)
            pc.constraint_region.primitive_poses.append(sphere_pose)
            c.position_constraints.append(pc)

            # Orientation constraint
            oc = OrientationConstraint()
            oc.header.frame_id = "world"
            oc.link_name = "tool0"
            oc.orientation.w = 1.0
            oc.absolute_x_axis_tolerance = 0.3
            oc.absolute_y_axis_tolerance = 0.3
            oc.absolute_z_axis_tolerance = 0.3
            oc.weight = 1.0
            c.orientation_constraints.append(oc)

            request.goal_constraints.append(c)
            planning_options = PlanningOptions()
            planning_options.planning_scene_diff.is_diff = True
            planning_options.planning_scene_diff.robot_state.is_diff = True

            goal.request = request
            goal.planning_options = planning_options

            send_goal_future = self.move_client.send_goal_async(goal)
            rclpy.spin_until_future_complete(self, send_goal_future)
            goal_handle = send_goal_future.result()
            if not goal_handle or not goal_handle.accepted:
                self.get_logger().warn("Goal was rejected. Retrying...")
                time.sleep(1.0)
                continue

            # Wait for result
            result_future = goal_handle.get_result_async()
            rclpy.spin_until_future_complete(self, result_future)
            result = result_future.result().result
            if result.error_code.val == MoveItErrorCodes.SUCCESS:
                self.get_logger().info("Motion plan + execution succeeded!")
                return True
            else:
                err_code = result.error_code.val
                self.get_logger().warn(
                    f"Motion failed: code={err_code} ({moveit_error_string(err_code)})"
                )
                time.sleep(1.0)

        self.get_logger().error("All attempts to plan this motion failed!")
        return False

    # --------------------------------------------------------------------------
    # DEMO SEQUENCE
    # --------------------------------------------------------------------------
    def run_demo(self):
        # 1) Add a cylinder at x=0.6, y=0.0, z=0.8
        self.add_collision_object("my_cylinder")

        # 2) Move the end effector near that object (above it)
        self.move_ee_to_pose(x=1.184, y=1.281, z=1.33)

        # 3) Attach the object to "gripper_base"
        self.attach_object("my_cylinder", link_name="gripper_base")

        # 4) Move to a new location (the cylinder should follow in RViz)
        self.move_ee_to_pose(x=1.184, y=1.281, z=1.7)

        # 5) Detach
        self.detach_object("my_cylinder", link_name="gripper_base")

        # 6) Remove from the scene
        self.remove_object("my_cylinder")
        self.get_logger().info("Demo finished!")

def main(args=None):
    rclpy.init(args=args)
    node = AttachExampleNode()

    try:
        node.run_demo()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
