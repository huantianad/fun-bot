import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from glob import glob
from typing import Optional

import discord
from cogwatch import watch
from discord.ext import commands
from yaml import safe_load

from .help import Help
from .lang import send_embed


def read_config():
    with open('config.yaml') as config_file:
        config = safe_load(config_file)
    return config


@dataclass
class ClientData:
    queue: set[str] = field(default_factory=set)
    now_playing: str = str()
    channel: Optional[discord.TextChannel] = None
    message: Optional[discord.Message] = None


class FunBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="&", intents=discord.Intents.all(), help_command=Help(), case_insensitive=True)
        self.add_check(self.global_check)

        self.config = read_config()
        self.token = self.config['Bot']['token']
        self.color = discord.Color.gold()

        self.music_data = defaultdict(ClientData)

    @watch(path='bot/cogs')
    async def on_ready(self):
        self.load_cogs()

        print("Bot ready and cogs loaded.")

    def load_cogs(self):
        cog_list = glob('bot/cogs/*.py')

        for cog in self.config['Cogs']['blacklist']:
            try:
                cog_list.remove(f"bot/cogs/{cog}.py")
            except ValueError:
                pass

        for cog in cog_list:
            cog = cog.replace('/', '.')[:-3]
            self.load_extension(cog)
            print("Loaded", cog)

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
            argument = str(exc.param).split(':')[0]
            await send_embed(ctx, 'error.missing_required_argument', argument=argument)

        elif isinstance(exc, commands.CommandNotFound):
            failed_command = str(exc).split('"')[1]
            await send_embed(ctx, 'error.command_not_found', prefix=self.command_prefix, failed_command=failed_command)

        elif isinstance(exc, commands.MemberNotFound):
            await send_embed(ctx, 'error.member_not_found', user=exc.argument)

        elif isinstance(exc, (commands.NotOwner, commands.MissingPermissions)):
            await send_embed(ctx, 'error.missing_permissions')

        elif isinstance(exc, commands.CheckFailure):
            pass

        else:
            await self.unhandled_error(ctx, exc)
