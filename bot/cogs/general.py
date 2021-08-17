import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord.ext import commands
from discord import ui

from ..help import FunHelp
from ..lang import send_embed
from ..main import FunBot


def delta_to_string(delta: timedelta) -> str:
    """Convert a timedelta into human-readable text"""
    output = []

    days = delta.days
    seconds = delta.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days == 1:
        output.extend([days, 'day,', ])
    elif days:
        output.extend([days, 'days,'])

    if hours == 1:
        output.extend([hours, 'hour,'])
    elif hours:
        output.extend([hours, 'hours,'])

    if minutes == 1:
        output.extend([minutes, 'minute,'])
    elif minutes:
        output.extend([minutes, 'minutes,'])

    if seconds == 1:
        output.extend([seconds, 'second,'])
    elif seconds:
        output.extend([seconds, 'seconds,'])

    if not output:
        return '0 seconds'

    if len(output) >= 4:
        output.insert(-2, 'and')

    output[-1] = output[-1][:-1]  # Remove the comma from the last word
    if len(output) == 5:  # Don't include the oxford comma
        output[1] = output[1][:-1]  # exclude last char, should be comma.

    output = ' '.join([str(x) for x in output])

    return output


def parse_bounds(bounds: str) -> tuple[int, int]:
    if bounds is None:
        return 1, 100
    try:
        return 1, int(bounds)
    except ValueError:
        lower, upper = bounds.split('-')
        return int(lower), int(upper)


class General(commands.Cog):
    def __init__(self, bot: FunBot):
        self.bot = bot

        self.bot.help_command = FunHelp()
        self.bot.help_command.cog = self

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Pong!"""

        await send_embed(ctx, 'general.ping')

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        """Shows the uptime of the bot."""

        uptime = datetime.now(timezone.utc) - self.bot.startup_time
        await send_embed(ctx, 'general.uptime', uptime=delta_to_string(uptime))

    @commands.command()
    async def roll(self, ctx: commands.Context, bounds: Optional[str]):
        """Chooses a random number between the bounds given.
        The bounds should either be in the form `<upper>` or `<lower>-<upper>`.
        If no lower bound is given, 1 is used.
        If no upper bound is given, 100 is used.
        """

        try:
            lower, upper = parse_bounds(bounds)
            upper = max(upper, lower)
        except ValueError:
            await send_embed(ctx, 'general.error.roll_error')
            return

        value = random.randint(lower, upper)

        await send_embed(ctx, 'general.roll', user=ctx.author.mention, value=value, lower=lower, upper=upper)

    @commands.command(aliases=['coin'])
    async def flip(self, ctx: commands.Context):
        """Flips a coin!"""

        result = "heads" if random.randint(0, 1) == 1 else "tails"
        await send_embed(ctx, 'general.flip', result=result)

    @commands.command()
    async def button(self, ctx: commands.Context):
        """Aaaaaa"""

        class MyView(ui.View):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.count = 0

            @ui.button(emoji='😔', style=discord.ButtonStyle.green)
            async def button1(self, button: ui.Button, interaction: discord.Interaction):
                self.count += 1
                await interaction.message.edit(content=self.count)

        await ctx.send('message', view=MyView())


def setup(bot):
    bot.add_cog(General(bot))
