from typing import Optional

from discord import TextChannel
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Pong!"""

        await ctx.send("Pong!")

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def echo(self, ctx: commands.Context, channel: Optional[TextChannel], *, message: str):
        """Echo's a message into an optional channel"""

        await (channel or ctx).send(message)
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        """Turns off the bot"""

        for client in self.bot.voice_clients:
            await client.disconnect()

        await self.bot.close()


def setup(bot):
    bot.add_cog(General(bot))
