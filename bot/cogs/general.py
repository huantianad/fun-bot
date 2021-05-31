from datetime import datetime, timedelta, timezone
from typing import Optional

from discord import TextChannel
from discord.ext import commands

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


class General(commands.Cog):
    def __init__(self, bot: FunBot):
        self.bot = bot

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
    @commands.has_permissions(manage_guild=True)
    async def echo(self, ctx: commands.Context, channel: Optional[TextChannel], *, message: str):
        """Echo's a message into an optional channel"""

        await (channel or ctx).send(message)
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.is_owner()
    async def eval(self, ctx: commands.Context, *, expression: str):
        """Evaluates a python expression"""

        await send_embed(ctx, 'general.eval', result=eval(expression))

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        """Turns off the bot"""

        await send_embed(ctx, 'general.shutdown')

        for client in self.bot.voice_clients:
            await client.disconnect()

        await self.bot.close()


def setup(bot):
    bot.add_cog(General(bot))
