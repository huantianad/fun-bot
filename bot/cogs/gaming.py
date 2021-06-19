import asyncio
from typing import Optional, Iterator, Union

import discord
from discord.ext import commands

from ..main import FunBot


class TTTGame:
    def __init__(self, ctx: commands.Context, player_2: discord.Member) -> None:
        self.ctx = ctx
        self.player_1 = ctx.author
        self.player_2 = player_2
        self.current_player = self.player_1

        self.grid = TTTGrid()

        self.reaction_emojis = {
            u"\u2196": (0, 0),
            u"\u2B06": (0, 1),
            u"\u2197": (0, 2),
            u"\u2B05": (1, 0),
            u"\u23FA": (1, 1),
            u"\u27A1": (1, 2),
            u"\u2199": (2, 0),
            u"\u2B07": (2, 1),
            u"\u2198": (2, 2)
        }

    async def start(self) -> None:
        # Send the initial message
        self.message: discord.Message = await self.ctx.send(embed=self.make_embed())

        # Add the reactions which act as controls
        for emoji in self.reaction_emojis:
            await self.message.add_reaction(emoji)

        # do_turn returns self.grid.check_for_end(), so it is None with the game hasn't finished
        while self.grid.check_for_end() is None:
            await self.do_turn()

    async def do_turn(self) -> None:
        reaction, user = await self.ctx.bot.wait_for("reaction_add", check=self.check, timeout=60*60*24)
        row, col = self.reaction_emojis[reaction.emoji]

        # Modify the actual grid with the move
        self.grid.grid[row][col] = 1 if self.current_player == self.player_1 else 2

        # Swap the current player with the other player
        self.current_player = self.player_1 if self.current_player == self.player_2 else self.player_2
        await self.message.edit(embed=self.make_embed())

    def make_embed(self) -> discord.Embed:
        winner = self.get_winner()
        message = (f"{self.current_player.mention}'s turn!" if winner is None
                   else f"{winner.mention} has won!" if winner != "draw"
                   else "It's a draw!")

        description = f"{self.player_1.mention} vs. {self.player_2.mention}\n{message}"
        embed = discord.Embed(title="Tic-Tac-Toe!", description=description, color=discord.Color.gold())
        embed.add_field(name="Grid", value=self.grid.pretty_grid())

        return embed

    def get_winner(self) -> Union[discord.Member, int, None]:
        return {1: self.player_1, 2: self.player_2, 3: "draw"}.get(self.grid.check_for_end())

    def check(self, r: discord.Reaction, u: discord.User) -> bool:
        index = self.reaction_emojis.get(r.emoji)
        if index is None:
            return
        row, col = index

        return u == self.current_player and self.grid.grid[row][col] == 0


class TTTGrid:
    def __init__(self) -> None:
        self.grid = [[0] * 3 for _ in range(3)]

        self.grid_emojis = {
            0: ":white_large_square:",
            1: ":regional_indicator_x:",
            2: ":o2:"
        }

    def pretty_grid(self) -> str:
        str_grid = "\n".join("".join(map(str, row)) for row in self.grid)  # Adds a new line every three emojis.
        for value, emoji in self.grid_emojis.items():
            str_grid = str_grid.replace(str(value), emoji)

        return str_grid

    def check_for_end(self) -> Optional[int]:
        if self.is_winner(1):
            return 1

        if self.is_winner(2):
            return 2

        if 0 not in [value for row in self.grid for value in row]:  # All the spots are filled => draw
            return 3

        return None

    def is_winner(self, player_int: int) -> bool:
        for indexes in self.win_indexes():
            if all(self.grid[r][c] == player_int for r, c in indexes):
                return True

        return False

    def win_indexes(self) -> Iterator[Iterator[tuple[int, int]]]:
        n = 3  # Number of rows/cols in grid

        for r in range(n):  # Rows
            yield ((r, c) for c in range(n))

        for c in range(n):  # Columns
            yield ((r, c) for r in range(n))

        yield ((i, i) for i in range(n))  # Diagonal top left to bottom right
        yield ((i, n - 1 - i) for i in range(n))  # Diagonal top right to bottom left


class Gaming(commands.Cog):
    def __init__(self, bot: FunBot) -> None:
        self.bot = bot

    @commands.command()
    async def ttt(self, ctx: commands.Context, *, player_2: Optional[discord.Member]):
        """Start a tic-tac-toe game with another person!"""

        if player_2 is None or player_2.bot or player_2 == ctx.author:
            await ctx.send("Specify another player.")
            return

        try:
            await TTTGame(ctx, player_2).start()
        except asyncio.TimeoutError:
            pass


def setup(bot):
    bot.add_cog(Gaming(bot))
