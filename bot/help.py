from typing import Mapping, Optional

import discord
from discord.ext import commands


class FunHelp(commands.MinimalHelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self.color = discord.Color.gold()

    async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], list[commands.Command]]) -> None:
        embed = discord.Embed(title="Command Help", description=self.get_ending_note(), color=self.color)

        for cog, cog_commands in mapping.items():
            if cog:
                field_name = cog.qualified_name + ':'
                field_value = self.command_lister(cog_commands) if cog.get_commands() else "No commands!"

            elif cog_commands:
                field_name = "No category"
                field_value = self.command_lister(cog_commands)

            else:
                continue

            embed.add_field(name=field_name, value=field_value)

        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        embed = discord.Embed(title=f"{cog.qualified_name} Help", description=self.get_ending_note(), color=self.color)

        field_value = self.command_lister(cog.get_commands()) if cog.get_commands() else "No commands!"
        embed.add_field(name="Commands:", value=field_value)

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command: commands.Command) -> None:
        embed = discord.Embed(title=self.get_command_signature(command), color=self.color)

        if command.help:
            embed.description = command.help

        if alias := command.aliases:
            embed.add_field(name="Aliases", value=f"`{'`, `'.join(alias)}`", inline=False)

        await self.get_destination().send(embed=embed)

    def get_ending_note(self) -> str:
        command_name = self.invoked_with
        return f"""Type `{self.clean_prefix}{command_name} <command>` for more info on a command.
            You can also use `{self.clean_prefix}{command_name} <category>` for more info on a category."""

    def command_not_found(self, string) -> str:
        return f"No command called `{string}` found."

    def subcommand_not_found(self, command, string) -> str:
        if isinstance(command, discord.Group) and len(command.all_commands) > 0:
            return f'Command "{command.qualified_name}" has no subcommand named {string}'
        return f'Command "{command.qualified_name}" has no subcommands.'

    async def send_error_message(self, error: str) -> None:
        destination = self.get_destination()
        embed = discord.Embed(description=error, color=self.color)

        await destination.send(embed=embed)

    def get_command_signature(self, command: commands.Command) -> str:
        return f'{self.clean_prefix}{command.qualified_name} {command.signature}'.strip()

    def command_lister(self, command_list: list[commands.Command]) -> str:
        return '\n'.join([f"`{self.get_command_signature(x)}`" for x in command_list])
