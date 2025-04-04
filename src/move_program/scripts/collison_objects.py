#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose
from moveit_msgs.msg import CollisionObject

class SceneObjectsNode(Node):
    def __init__(self):
        super().__init__("scene_objects_node")
        self.collision_pub = self.create_publisher(CollisionObject, "collision_object", 10)
        self.timer = self.create_timer(2.0, self.add_all_once)
        self.done = False

    def add_all_once(self):
        if self.done:
            return
        self.done = True

        self.get_logger().info("Adding environment collisions for CylinderTable, RoboticArmBase, trays, cups, etc...")

        # 1) Cylinder Table
        self.add_cylinder_table()

        # 2) Robotic Arm Base
        self.add_robotic_arm_base()

        # 3) Two tables
        self.add_table("table1", 1.09717619, 1.39642)
        self.add_table("table2", 1.08436, 0.0708296)

        # 4) Trays
        self.add_tray1()  # using the multiple collisions from tray_model
        self.add_tray2()

        # 5) Cups
        # self.add_cup("red_cup", 0.973062, 1.295022) 
        # self.add_cup("green_cup", 1.148940, 1.295022)      
        # self.add_cup("blue_cup", 1.324818, 1.295022)
        # self.add_cup("yellow_cup", 0.973062, 1.451358)    
        # self.add_cup("purple_cup", 1.148940, 1.451358)

    # -------------------------------------------------------------------------
    #  Cylinder Table
    # -------------------------------------------------------------------------
    def add_cylinder_table(self):
        """
        SDF: 
          pose: (1.06135, 0.733805, 0.499153), radius=0.2, length=1.
        That is presumably the cylinder's center. 
        """
        cyl_obj = CollisionObject()
        cyl_obj.id = "cylinder_table"
        cyl_obj.header.frame_id = "world"

        cyl_prim = SolidPrimitive()
        cyl_prim.type = SolidPrimitive.CYLINDER
        cyl_prim.dimensions = [1.0, 0.2]  # [height, radius]

        p = Pose()
        p.position.x = 1.06135
        p.position.y = 0.733805
        p.position.z = 0.499153
        p.orientation.w = 1.0

        cyl_obj.primitives.append(cyl_prim)
        cyl_obj.primitive_poses.append(p)
        cyl_obj.operation = CollisionObject.ADD

        self.collision_pub.publish(cyl_obj)
        self.get_logger().info("Added cylinder_table collision")

    # -------------------------------------------------------------------------
    #  Robotic Arm Base
    # -------------------------------------------------------------------------
    def add_robotic_arm_base(self):
        """
        SDF: 
          pose = (1.06135, 0.73380, 1.05).
        Box size is 0.2×0.2×0.1, with the bottom at 1.05 => center is 1.05 + 0.05=1.10 
        """
        base_obj = CollisionObject()
        base_obj.id = "robotic_arm_base"
        base_obj.header.frame_id = "world"

        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = [0.2, 0.2, 0.1]  # from URDF / SDF

        p = Pose()
        p.position.x = 1.06135
        p.position.y = 0.73380
        p.position.z = 1.05
        p.orientation.w = 1.0

        base_obj.primitives.append(box)
        base_obj.primitive_poses.append(p)
        base_obj.operation = CollisionObject.ADD

        self.collision_pub.publish(base_obj)
        self.get_logger().info("Added robotic_arm_base collision")

    # -------------------------------------------------------------------------
    #  Table 1 & Table 2
    # -------------------------------------------------------------------------
    def add_table(self, table_id, x, y):
        """
        The table SDF: top is 1.5×0.8, thickness 0.03, plus 1m legs => total ~1.0 height
        We'll approximate as a single bounding box, 1.5×0.8×1.0, with bottom at z=0 => center=0.5
        Pose from SDF is (x, y, 0). So center => z=0.5
        """
        tab_obj = CollisionObject()
        tab_obj.id = table_id
        tab_obj.header.frame_id = "world"

        tab_box = SolidPrimitive()
        tab_box.type = SolidPrimitive.BOX
        # entire table bounding => 1.5 x 0.8 x 1.0
        tab_box.dimensions = [1.5, 0.8, 1.0]

        p = Pose()
        p.position.x = x
        p.position.y = y
        # bottom is 0 => center=0.5
        p.position.z = 0.5
        p.orientation.w = 1.0

        tab_obj.primitives.append(tab_box)
        tab_obj.primitive_poses.append(p)
        tab_obj.operation = CollisionObject.ADD

        self.collision_pub.publish(tab_obj)
        self.get_logger().info(f"Added {table_id}")

    # -------------------------------------------------------------------------
    #  Tray1
    # -------------------------------------------------------------------------
    def add_tray1(self):
        """
        SDF pose: (1.14894, 1.37319, 1.0151) + orientation ~ 1.57 about Z
        The tray's 'tray_model.txt' has multiple collisions: 
          main rectangle: ~0.469×0.7035×0.0059 at center 
          plus 4 side walls each 0.074×0.469×0.0128
        Let's replicate them as 5 boxes with correct offsets (like the real tray_model).
        """
        tray_obj = CollisionObject()
        tray_obj.id = "tray1"
        tray_obj.header.frame_id = "world"
        tray_obj.operation = CollisionObject.ADD

        # main base collision
        main_box = SolidPrimitive()
        main_box.type = SolidPrimitive.BOX
        # size=0.469×0.7035×0.0059
        main_box.dimensions = [0.469, 0.7035, 0.0059]

        main_pose = Pose()
        # SDF pose => 1.14894, 1.37319, 1.0151
        # We interpret that as the link frame at center of the base
        main_pose.position.x = 1.14894
        main_pose.position.y = 1.37319
        main_pose.position.z = 1.0151
        # orientation around Z by 1.57 => we do a quaternion
        # roll=pitch=0, yaw=1.57
        import math
        yaw = 1.57
        main_pose.orientation.w = math.cos(yaw/2.0)
        main_pose.orientation.z = math.sin(yaw/2.0)

        tray_obj.primitives.append(main_box)
        tray_obj.primitive_poses.append(main_pose)

        # 4 side walls (like the tray_model):
        # each has size= 0.074084×0.469×0.012815, with some offset
        # We'll replicate the 4 collisions with the same approach
        # For brevity, let's define them quickly:

        def add_side_wall(dx, dy, dz, rx, ry, rz, size, object_msg):
            wall = SolidPrimitive()
            wall.type = SolidPrimitive.BOX
            wall.dimensions = size  # [X, Y, Z]
            wpose = Pose()
            wpose.position.x = dx
            wpose.position.y = dy
            wpose.position.z = dz
            # small rotation about X or Y might be needed if tray_model had that
            # but in your SDF, we see "0.0 -0.942211 ???" for pitch?
            # Let's keep it simpler: we ignore those small rotations or
            # do them if you want to replicate exactly.
            wpose.orientation.w = 1.0
            object_msg.primitives.append(wall)
            object_msg.primitive_poses.append(wpose)

        # We'll do a local offset from the main base frame
        # *But*, because we have an orientation of 1.57 about Z, we'd have to transform
        # the side walls. For simplicity, let's just do 1 bounding box for the walls.

        # Or if you truly want all 4 walls, you must transform each offset
        # For a simpler approach, let's do "one big bounding box" that encloses the entire tray side region:
        #   Maybe 0.469 + 2*0.074 wide in one dimension, 0.7035 + 2*0.074 in the other, height= ~0.03
        #   We'll place it at the same center but bigger
        # A perfect replication of each sub-collision is quite involved with transforms.

        # We'll do a simpler approach: a second bounding box that is 0.62 x 0.85 x 0.04, to represent the tray + walls:
        walls = SolidPrimitive()
        walls.type = SolidPrimitive.BOX
        walls.dimensions = [0.62, 0.85, 0.04]
        walls_pose = Pose()
        # same center as main base, but z offset maybe +0.02 so it's on top?
        walls_pose.position.x = 1.14894
        walls_pose.position.y = 1.37319
        walls_pose.position.z = 1.0151
        walls_pose.orientation.w = main_pose.orientation.w
        walls_pose.orientation.z = main_pose.orientation.z

        tray_obj.primitives.append(walls)
        tray_obj.primitive_poses.append(walls_pose)

        self.collision_pub.publish(tray_obj)
        self.get_logger().info("Added tray1 with base + walls")

    # -------------------------------------------------------------------------
    #  Tray2 (same logic)
    # -------------------------------------------------------------------------
    def add_tray2(self):
        tray2_obj = CollisionObject()
        tray2_obj.id = "tray2"
        tray2_obj.header.frame_id = "world"
        tray2_obj.operation = CollisionObject.ADD

        import math

        # base box
        base_box = SolidPrimitive()
        base_box.type = SolidPrimitive.BOX
        base_box.dimensions = [0.469, 0.7035, 0.0059]

        base_pose = Pose()
        base_pose.position.x = 1.10565
        base_pose.position.y = 0.0825874
        base_pose.position.z = 1.0144893
        # orientation ~ 1.57 about Z
        yaw = 1.57
        base_pose.orientation.w = math.cos(yaw/2.0)
        base_pose.orientation.z = math.sin(yaw/2.0)

        tray2_obj.primitives.append(base_box)
        tray2_obj.primitive_poses.append(base_pose)

        # bounding box for walls
        walls_box = SolidPrimitive()
        walls_box.type = SolidPrimitive.BOX
        walls_box.dimensions = [0.62, 0.85, 0.04]

        walls_pose = Pose()
        walls_pose.position.x = base_pose.position.x
        walls_pose.position.y = base_pose.position.y
        walls_pose.position.z = base_pose.position.z
        walls_pose.orientation.w = base_pose.orientation.w
        walls_pose.orientation.z = base_pose.orientation.z

        tray2_obj.primitives.append(walls_box)
        tray2_obj.primitive_poses.append(walls_pose)

        self.collision_pub.publish(tray2_obj)
        self.get_logger().info("Added tray2 with base + walls")

    # -------------------------------------------------------------------------
    #  Cups
    # -------------------------------------------------------------------------
    def add_cup(self, cup_id, x, y):
        """
        Each SDF for cups has ~0.13 height, top radius ~0.056
        The SDF says <pose> = (x, y, 1.0988185) is the bottom.
        But the mesh is offset by 0.0325 => total from bottom to top ~ 0.13
        We'll do a bounding cylinder: radius=0.056, height=0.13
        center = bottom + 0.13/2 => ~ 1.0988185 + 0.065 => 1.1638185
        plus 0.0325? Actually the link pose includes that offset, so let's be direct:
        final center = 1.0988185 + (0.13/2)=1.1638185
        """
        cup_obj = CollisionObject()
        cup_obj.id = cup_id
        cup_obj.header.frame_id = "world"

        cyl = SolidPrimitive()
        cyl.type = SolidPrimitive.CYLINDER
        cyl.dimensions = [0.15, 0.075]  # height=0.13, radius=0.056

        p = Pose()
        p.position.x = x
        p.position.y = y
        p.position.z = 1.088953
        p.orientation.w = 1.0

        cup_obj.primitives.append(cyl)
        cup_obj.primitive_poses.append(p)
        cup_obj.operation = CollisionObject.ADD

        self.collision_pub.publish(cup_obj)
        self.get_logger().info(f"Added {cup_id}")

def main(args=None):
    rclpy.init(args=args)
    node = SceneObjectsNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
