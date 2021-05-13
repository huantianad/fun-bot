import discord
from discord.ext import commands


class Help(commands.DefaultHelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self.color = discord.Color.gold()

    def get_ending_note(self):
        command_name = self.invoked_with
        return f"Type `{self.clean_prefix}{command_name} <command>` for more info on a command."

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Command Help", description=self.get_ending_note(), color=self.color)
        for cog in mapping:
            if cog:
                if cog.get_commands():
                    commands_stuff = '\n'.join([x.name for x in cog.get_commands()])
                    embed.add_field(name=cog.qualified_name, value=commands_stuff)
                else:
                    embed.add_field(name=cog.qualified_name, value="No commands!")

        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title=f"{cog.qualified_name} Help", description=self.get_ending_note(), color=self.color)
        if cog.get_commands():
            commands_stuff = '\n'.join([x.name for x in cog.get_commands()])
            embed.add_field(name=cog.qualified_name, value=commands_stuff)
        else:
            embed.add_field(name=cog.qualified_name, value="No commands!")

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=f"{self.clean_prefix}{command.name}", color=self.color)
        if command.help:
            embed.description = command.help
        embed.add_field(name='Syntax:', value=f"`{self.get_command_signature(command).strip()}`")

        await self.get_destination().send(embed=embed)
