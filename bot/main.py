import traceback
from collections import defaultdict
from configparser import ConfigParser
from dataclasses import dataclass, field
from glob import glob
from typing import Union

import discord
from cogwatch import watch
from discord.ext import commands

from .help import Help


def read_config():
    config = ConfigParser()
    config.read('config.ini')
    return config['Bot']


@dataclass
class ClientData:
    queue: set[str] = field(default_factory=set)
    now_playing: str = str()
    channel: Union[None, discord.TextChannel] = None
    message: Union[None, discord.Message] = None


class FunBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="&", intents=discord.Intents.all(), help_command=Help(), case_insensitive=True)
        self.add_check(self.global_check)

        self.config = read_config()
        self.color = discord.Color.gold()

        self.music_data = defaultdict(ClientData)

    @watch(path='bot/cogs')
    async def on_ready(self):
        cog_list = glob('bot/cogs/*.py')

        for cog in cog_list:
            cog = cog.replace('/', '.')[:-3]
            self.load_extension(cog)
            print("Loaded", cog)

        print("Bot ready and cogs loaded.")

    async def global_check(self, ctx: commands.Context):
        await self.wait_until_ready()
        return ctx.guild is not None

    async def unhandled_error(self, ctx: commands.Context, exc: Exception):
        # there's an exception that I didn't have a handle for. This is bad.
        print(exc)
        await ctx.send("Something bad happened! <@!300050030923087872> pls fix.")
        await ctx.send(f"`{exc}`")
        if hasattr(exc, "original"):
            await ctx.send(f"```{''.join(traceback.format_tb(exc.original.__traceback__))}```")
        await ctx.send(f"```{''.join(traceback.format_tb(exc.__traceback__))}```")

    async def on_command_error(self, ctx: commands.Context, exc: Exception):
        if isinstance(exc, commands.MissingRequiredArgument):
            await ctx.send(f"The argument `{str(exc.param).split(':')[0]}` is required.")

        elif isinstance(exc, commands.CommandNotFound):
            failed_command = str(exc).split('"')[1]
            await ctx.send(f"The command `{self.command_prefix}{failed_command}` doesn't actually exist.")

        elif isinstance(exc, commands.MemberNotFound):
            await ctx.send(f'The user "{exc.argument}" was not found.')

        elif isinstance(exc, commands.CheckFailure):
            pass
        else:
            await self.unhandled_error(ctx, exc)
