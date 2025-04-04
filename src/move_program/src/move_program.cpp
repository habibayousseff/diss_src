// #include <memory>
// #include <sstream>
// #include <rclcpp/rclcpp.hpp>
// #include <moveit/move_group_interface/move_group_interface.hpp>
// #include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
// #include <tf2/LinearMath/Quaternion.h>
// #include <geometry_msgs/msg/pose.hpp>

// int main(int argc, char *argv[])
// {
//     // Initialize ROS 2
//     rclcpp::init(argc, argv);

//     // Create the node with automatic parameter declaration enabled.
//     auto node = std::make_shared<rclcpp::Node>(
//         "ur_move_program",
//         rclcpp::NodeOptions().automatically_declare_parameters_from_overrides(true)
//     );
//     auto logger = rclcpp::get_logger("ur_move_program");

//     // Ensure use_sim_time is set (it should be provided by the launch file).
//     if (!node->has_parameter("use_sim_time"))
//         node->declare_parameter("use_sim_time", true);
//     node->set_parameter(rclcpp::Parameter("use_sim_time", true));

//     // Get the robot_description parameter (set via the launch file).
//     std::string robot_description;
//     if (!node->get_parameter("robot_description", robot_description) || robot_description.empty())
//     {
//         RCLCPP_ERROR(logger, "robot_description parameter is not set. Please launch with a proper launch file.");
//         // return 1;
//     }
//     else
//     {
//         RCLCPP_INFO(logger, "robot_description parameter loaded successfully.");
//     }

//     // Optionally, check for the robot_description_semantic parameter.
//     std::string robot_description_semantic;
//     if (!node->get_parameter("robot_description_semantic", robot_description_semantic) || robot_description_semantic.empty())
//     {
//         RCLCPP_WARN(logger, "robot_description_semantic parameter not found. Planning may not work as expected.");
//     }

//     // Wait a short time to ensure Move Group services are available.
//     RCLCPP_INFO(logger, "Waiting for Move Group to become available...");
//     rclcpp::sleep_for(std::chrono::seconds(2));

//     // Initialize the Move Group Interface for the planning group "ur_manipulator".
//     moveit::planning_interface::MoveGroupInterface move_group(node, "ur_manipulator");

//     if (move_group.getName().empty())
//     {
//         RCLCPP_ERROR(logger, "Move Group Interface failed to initialize!");
//         return 1;
//     }
//     RCLCPP_INFO(logger, "Move Group Interface successfully initialized.");
//     RCLCPP_INFO(logger, "Planning frame: %s", move_group.getPlanningFrame().c_str());
//     RCLCPP_INFO(logger, "End effector link: %s", move_group.getEndEffectorLink().c_str());

//     // Define a new goal pose.
//     // Here we set an orientation with a 90° rotation about the z-axis.
//     tf2::Quaternion tf2_quat;
//     tf2_quat.setRPY(0, 0, 1.5708);  // 90 degrees in radians

//     geometry_msgs::msg::Pose goal_pose;
//     goal_pose.orientation = tf2::toMsg(tf2_quat);

//     // Set a goal position that is reachable based on typical UR5 dimensions.
//     goal_pose.position.x = 0.3;  // slightly forward from the base center
//     goal_pose.position.y = 0.0;  // centered laterally
//     goal_pose.position.z = 0.5;  // a reasonable height

//     move_group.setPoseTarget(goal_pose);

//     // Plan the motion
//     moveit::planning_interface::MoveGroupInterface::Plan plan;
//     bool success = static_cast<bool>(move_group.plan(plan));

//     if (success)
//     {
//         RCLCPP_INFO(logger, "Planning successful! Executing the motion plan...");
//         move_group.execute(plan);
//     }
//     else
//     {
//         RCLCPP_ERROR(logger, "Motion planning failed! No valid path found.");
//     }

//     rclcpp::shutdown();
//     return 0;
// }



















// #include <memory>
// #include <sstream>
// #include <rclcpp/rclcpp.hpp>
// #include <moveit/move_group_interface/move_group_interface.hpp>
// #include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
// #include <tf2/LinearMath/Quaternion.h>
// #include <geometry_msgs/msg/pose.hpp>

// int main(int argc, char *argv[])
// {
//     rclcpp::init(argc, argv);
//     auto node = std::make_shared<rclcpp::Node>("ur_move_program");
//     auto logger = rclcpp::get_logger("ur_move_program");

//     // Make sure your node has the robot_description parameter, etc.

//     // 1) Create the MoveGroupInterface for your manipulator group
//     moveit::planning_interface::MoveGroupInterface move_group(node, "ur_manipulator");
//     RCLCPP_INFO(logger, "End effector link: %s", move_group.getEndEffectorLink().c_str());

//     // 2) Define the goal pose (x, y, z) from the green cup
//     geometry_msgs::msg::Pose cup_pose;
//     cup_pose.position.x = 1.5032808495243333;
//     cup_pose.position.y = 1.2192895967851423;
//     cup_pose.position.z = 1.1601111872246088;

//     // 3) Set orientation to roll=0, pitch=0, yaw=0
//     tf2::Quaternion q;
//     q.setRPY(0, 0, 0);  // no rotation
//     cup_pose.orientation = tf2::toMsg(q);

//     // 4) Pass this pose to MoveIt as a target
//     move_group.setPoseTarget(cup_pose);

//     // 5) Plan and execute
//     moveit::planning_interface::MoveGroupInterface::Plan plan;
//     bool success = static_cast<bool>(move_group.plan(plan));

//     if (success)
//     {
//         RCLCPP_INFO(logger, "Planning successful! Executing...");
//         move_group.execute(plan);
//     }
//     else
//     {
//         RCLCPP_ERROR(logger, "Motion planning failed! No valid path found.");
//     }

//     rclcpp::shutdown();
//     return 0;
// }
















// #include <memory>
// #include <rclcpp/rclcpp.hpp>

// // MoveIt
// #include <moveit/move_group_interface/move_group_interface.h>
// #include <moveit_msgs/msg/move_it_error_codes.hpp>
// #include <moveit/robot_state/robot_state.h>  // often needed for the core namespace


// // TF / geometry
// #include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
// #include <geometry_msgs/msg/pose.hpp>

// using namespace std::chrono_literals;

// int main(int argc, char **argv)
// {
//   // Initialize ROS 2
//   rclcpp::init(argc, argv);

//   // Create the node; parameters (like robot_description) are assumed to be set by your launch files.
//   auto node = rclcpp::Node::make_shared("move_program");

//   // Allow some time for the parameter server and robot_description to be populated.
//   rclcpp::sleep_for(2s);

//   // Create a MoveGroupInterface object for your manipulator group (change "ur_manipulator" if needed).
//   moveit::planning_interface::MoveGroupInterface move_group(node, "ur_manipulator");

//   // (Optional) Set the end effector link explicitly.
//   // This tells MoveIt which link’s pose you want to control.
//   move_group.setEndEffectorLink("wrist_3_link");

//   // Define the target pose for the end-effector (e.g., the green cup's position).
//   geometry_msgs::msg::Pose target_pose;
//   target_pose.position.x = 1.5033;  // x-coordinate of the green cup
//   target_pose.position.y = 1.2193;  // y-coordinate
//   target_pose.position.z = 1.1601;  // z-coordinate

//   // Set an orientation.
//   // Here we use an identity quaternion (i.e. no rotation) – adjust if needed.
//   target_pose.orientation.x = 0.0;
//   target_pose.orientation.y = 0.0;
//   target_pose.orientation.z = 0.0;
//   target_pose.orientation.w = 1.0;

//   // Set the target pose for planning.
//   move_group.setPoseTarget(target_pose);

//   // Plan to the target pose.
//   moveit::planning_interface::MoveGroupInterface::Plan plan;
//   auto planning_result = move_group.plan(plan);

//   // Compare to moveit::core::MoveItErrorCode::SUCCESS
//   if (planning_result == moveit::core::MoveItErrorCode::SUCCESS)
//   {
//     RCLCPP_INFO(node->get_logger(), "Planning succeeded, executing trajectory...");
//     move_group.execute(plan);
//   }
//   else
//   {
//     RCLCPP_ERROR(node->get_logger(), "Planning failed!");
//   }

//   // Shutdown ROS 2.
//   rclcpp::shutdown();
//   return 0;
// }

































// #include <rclcpp/rclcpp.hpp>
// #include <moveit/move_group_interface/move_group_interface.h>
// #include <memory>

// class MoveProgram : public rclcpp::Node
// {
// public:
//   MoveProgram() : Node("move_program")
//   {
//     RCLCPP_INFO(get_logger(), "Node constructed. Will init MoveGroup soon...");
//   }

//   // Do MoveGroupInterface creation AFTER we are fully owned by a shared_ptr
//   void initMoveGroup()
//   {
//     // Now shared_from_this() is valid
//     move_group_ = std::make_shared<moveit::planning_interface::MoveGroupInterface>(
//         shared_from_this(), 
//         "ur_manipulator");

//     // Optionally set an end-effector link or other parameters
//     move_group_->setEndEffectorLink("wrist_3_link");
//     move_group_->setPlanningTime(10.0);

//     RCLCPP_INFO(get_logger(), "MoveGroupInterface created successfully!");
//   }

//   void moveToTarget()
//   {
//     // Example: define a simple target
//     geometry_msgs::msg::Pose target_pose;
//     target_pose.position.x = 0.4;
//     target_pose.position.y = -0.2;
//     target_pose.position.z = 0.3;
//     target_pose.orientation.w = 1.0;

//     move_group_->setPoseTarget(target_pose);

//     moveit::planning_interface::MoveGroupInterface::Plan plan;
//     bool success = (move_group_->plan(plan) == moveit::core::MoveItErrorCode::SUCCESS);

//     if (success)
//     {
//       RCLCPP_INFO(get_logger(), "Planning succeeded, executing...");
//       auto exec_status = move_group_->execute(plan);
//       if (exec_status == moveit::core::MoveItErrorCode::SUCCESS)
//         RCLCPP_INFO(get_logger(), "Execution complete!");
//       else
//         RCLCPP_ERROR(get_logger(), "Execution failed!");
//     }
//     else
//     {
//       RCLCPP_ERROR(get_logger(), "Planning failed!");
//     }
//   }

// private:
//   std::shared_ptr<moveit::planning_interface::MoveGroupInterface> move_group_;
// };

// int main(int argc, char** argv)
// {
//   rclcpp::init(argc, argv);

//   // Create the node via shared_ptr
//   auto node = std::make_shared<MoveProgram>();

//   // Now that node is fully owned by a shared_ptr, we can safely init MoveGroupInterface
//   node->initMoveGroup();

//   // Example: plan/execute a motion
//   node->moveToTarget();

//   // Spin if needed
//   rclcpp::spin(node);
//   rclcpp::shutdown();
//   return 0;
// }
















#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>
#include <moveit/move_group_interface/move_group_interface.hpp>
#include <geometry_msgs/msg/pose.hpp>
#include <mutex>
#include <condition_variable>
#include <thread>

using namespace std::chrono_literals;

// Subscriber node that waits for the robot_description
class RobotDescriptionSubscriber : public rclcpp::Node {
public:
  RobotDescriptionSubscriber() : Node("robot_description_subscriber") {
    // Create a subscription to the topic "robot_description_topic"
    subscription_ = this->create_subscription<std_msgs::msg::String>(
      "robot_description_topic", 10,
      [this](const std_msgs::msg::String::SharedPtr msg) {
        std::unique_lock<std::mutex> lock(mutex_);
        robot_description_ = msg->data;
        RCLCPP_INFO(this->get_logger(), "Received robot_description (first 100 chars): %s",
                    robot_description_.substr(0, 100).c_str());
        cv_.notify_all();
      });
  }

  // Wait until robot_description_ is non-empty
  std::string wait_for_robot_description() {
    std::unique_lock<std::mutex> lock(mutex_);
    cv_.wait(lock, [this] { return !robot_description_.empty(); });
    return robot_description_;
  }

private:
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription_;
  std::string robot_description_;
  std::mutex mutex_;
  std::condition_variable cv_;
};

class MoveProgram : public rclcpp::Node {
public:
  // Constructor: accepts the robot_description string.
  MoveProgram(const std::string & robot_description)
  : Node("move_program") {
    // Set the "robot_description" parameter locally.
    this->declare_parameter("robot_description", robot_description);

    // Create the MoveGroupInterface for the planning group "ur_manipulator".
    move_group_ = std::make_shared<moveit::planning_interface::MoveGroupInterface>(
      shared_from_this(), "ur_manipulator");

    // Set the end-effector link and planning time.
    move_group_->setEndEffectorLink("wrist_3_link");
    move_group_->setPlanningTime(10.0);

    // Print the current end-effector pose.
    geometry_msgs::msg::Pose current_pose = move_group_->getCurrentPose().pose;
    RCLCPP_INFO(this->get_logger(), "Current End-Effector Pose:\n  x: %.3f, y: %.3f, z: %.3f",
                current_pose.position.x, current_pose.position.y, current_pose.position.z);
  }

  // Function to move the robot to a target pose.
  void move_to_target(const geometry_msgs::msg::Pose & target_pose) {
    move_group_->setPoseTarget(target_pose);
    moveit::planning_interface::MoveGroupInterface::Plan plan;
    bool success = (move_group_->plan(plan) == moveit::core::MoveItErrorCode::SUCCESS);
    if (success) {
      RCLCPP_INFO(this->get_logger(), "Planning succeeded, executing trajectory...");
      auto exec_status = move_group_->execute(plan);
      if (exec_status == moveit::core::MoveItErrorCode::SUCCESS)
        RCLCPP_INFO(this->get_logger(), "Trajectory execution complete!");
      else
        RCLCPP_ERROR(this->get_logger(), "Execution failed!");
    } else {
      RCLCPP_ERROR(this->get_logger(), "Planning failed!");
    }
  }

private:
  std::shared_ptr<moveit::planning_interface::MoveGroupInterface> move_group_;
};

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);

  // Create the RobotDescriptionSubscriber to wait for the URDF string.
  auto robot_desc_sub = std::make_shared<RobotDescriptionSubscriber>();
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(robot_desc_sub);

  std::thread spin_thread([&executor]() { executor.spin(); });
  std::string robot_description = robot_desc_sub->wait_for_robot_description();
  executor.cancel();
  spin_thread.join();

  // Create the MoveProgram node using the retrieved robot_description.
  auto move_node = std::make_shared<MoveProgram>(robot_description);

  // Define a target pose and command the robot to move.
  geometry_msgs::msg::Pose target_pose;
  target_pose.position.x = 1.061;
  target_pose.position.y = 0.542;
  target_pose.position.z = 2.101;
  target_pose.orientation.w = 1.0;
  move_node->move_to_target(target_pose);

  rclcpp::spin(move_node);
  rclcpp::shutdown();
  return 0;
}
