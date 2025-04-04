#!/usr/bin/env python3
"""
llm_interface_node.py
A ROS 2 node that provides a text-based interface to an LLM (OpenAI GPT).
When you type "Go to red cup", it interprets that and calls your existing
move_to_named_goal() function (from 'predefined_object_navigation.py').
"""
import os
import sys
import rclpy
from rclpy.node import Node

# We'll need your predefined_object_navigation or a function from it
from move_program.nav import move_to_named_goal

# If you want GPT-4 via openai
import openai

class LLMInterfaceNode(Node):
    def __init__(self):
        super().__init__('llm_interface_node')
        # Set your OpenAI API key here or via env var
        # openai.api_key = os.getenv("OPENAI_API_KEY", "sk-REPLACE_THIS")
        openai.api_key = "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"


        self.get_logger().info("LLM Interface Node started. Type commands in console...")

        # Maybe run a short timer to poll for user input
        self.timer = self.create_timer(5.0, self.poll_user)
        self.busy = False

    def poll_user(self):
        if self.busy:
            return
        self.busy = True

        user_input = input("\nType a command (e.g. 'go to red cup'): ")
        if not user_input.strip():
            self.busy = False
            return

        # Step 1: Query the LLM
        response = self.query_llm(user_input)

        # Step 2: Parse the response for the color cup
        #  You can do something more advanced (like JSON).
        #  For now, let's do a naive approach to see if the LLM mentioned "red," "green," etc.
        self.get_logger().info(f"LLM says: {response}")

        # We'll manually parse for color keywords:
        # (In real usage, you'd want a more robust approach.)
        if "red" in response.lower():
            self.get_logger().info("LLM suggests red cup -> calling move_to_named_goal('RedCup')")
            move_to_named_goal(self, "RedCup")
        elif "green" in response.lower():
            self.get_logger().info("LLM suggests green cup -> calling move_to_named_goal('GreenCup')")
            move_to_named_goal(self, "GreenCup")
        elif "blue" in response.lower():
            self.get_logger().info("LLM suggests blue cup -> calling move_to_named_goal('BlueCup')")
            move_to_named_goal(self, "BlueCup")
        elif "yellow" in response.lower():
            self.get_logger().info("LLM suggests yellow cup -> calling move_to_named_goal('YellowCup')")
            move_to_named_goal(self, "YellowCup")
        elif "purple" in response.lower():
            self.get_logger().info("LLM suggests purple cup -> calling move_to_named_goal('PurpleCup')")
            move_to_named_goal(self, "PurpleCup")
        else:
            self.get_logger().info("LLM didn't mention a recognized cup color. Doing nothing.")

        self.busy = False

    def query_llm(self, prompt_text):
        """
        Minimal example call to GPT-4 or GPT-3.5 via openai.ChatCompletion
        """
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4",  # or "gpt-3.5-turbo" if you don't have GPT-4
                messages=[
                    {"role": "system", "content": "You are a helpful robotics assistant. We have cups named RedCup, GreenCup, BlueCup, YellowCup, PurpleCup. If user wants to go to or pick up a cup, respond with a suggestion that includes the color name."},
                    {"role": "user", "content": prompt_text},
                ],
                temperature=0.0,
            )
            return resp.choices[0].message["content"]
        except Exception as e:
            self.get_logger().error(f"OpenAI API error: {str(e)}")
            return "Error: could not query LLM"

def main(args=None):
    rclpy.init(args=args)
    node = LLMInterfaceNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
