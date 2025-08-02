import discord
from discord.ext import commands, tasks
import asyncio

# We will re-add the import here, as this is where the cog is loaded.
from usecmd import UseCommandCog

class ControllerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents)

        self.controller_token = self.load_token('controllertoken.txt')
        self.worker_tokens = self.load_tokens('tokens.txt')
        self.worker_bots = []
        self.dm_task = None

    async def setup_hook(self):
        # This is the correct place to load cogs in modern discord.py.
        # It runs after the bot is logged in but before it connects to the gateway.
        await self.add_cog(UseCommandCog(self))
        self.worker_login.start()

    def load_token(self, file_name):
        try:
            with open(file_name, 'r') as f:
                token = f.read().strip()
                print(f"Loaded controller token from {file_name}")
                return token
        except FileNotFoundError:
            print(f"Error: {file_name} not found.")
            return None

    def load_tokens(self, file_name):
        try:
            with open(file_name, 'r') as f:
                tokens = [line.strip() for line in f.readlines() if line.strip()]
                print(f"Loaded {len(tokens)} worker tokens from {file_name}")
                return tokens
        except FileNotFoundError:
            print(f"Error: {file_name} not found.")
            return []

    async def on_ready(self):
        print(f'Controller bot logged in as {self.user}')
        print('Waiting for worker bots to log in...')

    @tasks.loop(seconds=5.0)
    async def worker_login(self):
        if not self.worker_bots:
            await self.login_worker_bots()

    async def login_worker_bots(self):
        print("Attempting to log in worker bots...")
        if not self.worker_tokens:
            print("No worker tokens found. Cannot start worker bots.")
            return

        for i, token in enumerate(self.worker_tokens):
            worker = commands.Bot(command_prefix='!', intents=discord.Intents.all())
            self.worker_bots.append(worker)
            asyncio.create_task(self.run_worker_bot(worker, token, i + 1))

        while not all(worker.is_ready() for worker in self.worker_bots):
            await asyncio.sleep(1)

        print(f'All {len(self.worker_bots)} worker bots are online.')
        self.worker_login.cancel()

    async def run_worker_bot(self, worker, token, bot_number):
        try:
            await worker.start(token)
            print(f"Worker bot #{bot_number} logged in.")
        except discord.errors.LoginFailure:
            print(f"Error: Improper token for worker bot #{bot_number}.")
            self.worker_bots.remove(worker)
        except Exception as e:
            print(f"An unexpected error occurred with worker bot #{bot_number}: {e}")
            self.worker_bots.remove(worker)

    def run_controller(self):
        if not self.controller_token:
            print("Controller token not loaded. Aborting.")
            return
        try:
            print("Attempting to run controller bot...")
            self.run(self.controller_token)
        except discord.errors.LoginFailure:
            print("Error: Improper token for the controller bot.")
        except Exception as e:
            print(f"An unexpected error occurred while running the controller bot: {e}")
