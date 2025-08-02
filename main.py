import discord
from controller import ControllerBot
import asyncio

# Create the controller bot instance and run it
if __name__ == "__main__":
    controller_bot = ControllerBot()
    controller_bot.run_controller()
