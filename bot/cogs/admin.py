from typing import Optional

import discord
from discord.ext import commands

from ..lang import send_embed
from ..main import FunBot


class Admin(commands.Cog):
    def __init__(self, bot: FunBot):
        self.bot = bot

    @commands.command(aliases=['tell'])
    @commands.has_permissions(manage_guild=True)
    async def echo(self, ctx: commands.Context, channel: Optional[discord.TextChannel], *, message: str):
        """Echo's a message into an optional channel"""

        await (channel or ctx).send(message)
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.is_owner()
    async def eval(self, ctx: commands.Context, *, expression: str):
        """Evaluates a python expression"""

        await send_embed(ctx, 'admin.eval', result=eval(expression))

    @commands.command()
    @commands.is_owner()
    async def exec(self, ctx: commands.Context, *, statement: str):
        """Executes a python statement"""

        # Make an async function with the code and `exec` it
        exec(
            'async def __ex(ctx): ' +
            ''.join(f'\n {line}' for line in statement.split('\n'))
        )

        # Get `__ex` from local variables, call it and return the result
        return await locals()['__ex'](ctx)

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        """Turns off the bot"""

        await send_embed(ctx, 'admin.shutdown')

        for client in self.bot.voice_clients:
            await client.disconnect()

        await self.bot.close()


def setup(bot):
    bot.add_cog(Admin(bot))
