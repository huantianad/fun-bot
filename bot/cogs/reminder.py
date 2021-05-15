import json
from datetime import datetime

from discord import Color, Embed
from discord.ext import commands, tasks

from ..main import FunBot


class Reminder(commands.Cog):
    def __init__(self, bot: FunBot):
        self.bot = bot
        self.main_loop.start()
        self.reminder_enabled = True

        self.numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        self.check_x = ["✔️", "✖️"]
        self.color = self.bot.color

    @commands.command()
    async def register(self, ctx: commands.Context):
        """Register yourself for the notifications."""

        with open("user_data.json", "r+") as file:
            file_data = json.load(file)

        if str(ctx.author.id) in file_data:  # Give error if the user is already registered
            embed = Embed(description="You are already registered! Do `&unregister` to unregister first.",
                          color=Color.red())
            await ctx.send(embed=embed)
            return

        user_data = {}
        """ This code is unnecessary for one grade only
        # Ask the user what their first period is
        message = await ctx.send(embed=Embed(title="Setup 1/3",
                                             description="What is your first period?\n"
                                                         "Period 0️⃣ starts at 7:30\n"
                                                         "Period 1️⃣ starts at 8:35"))
        for emoji in self.numbers[:2]:
            await message.add_reaction(emoji)

        def check(r, u):
            return r.emoji in self.numbers and u == ctx.author
        reaction, user = await self.bot.wait_for("reaction_add", check=check)
        user_data["start_period"] = self.numbers.index(reaction.emoji)
        print(user_data)

        # Ask the user what their last period is
        message = await ctx.send(embed=Embed(title="Setup 2/3",
                                             description="What is your last period?\n"
                                                         "Period 7️⃣ starts at 2:05\n"
                                                         "Period 8️⃣ starts at 3:00"))
        for emoji in self.numbers[7:9]:
            await message.add_reaction(emoji)

        reaction, user = await self.bot.wait_for("reaction_add", check=check)
        user_data["end_period"] = self.numbers.index(reaction.emoji)
        print(user_data)"""

        # Ask the user what their lunch period is
        message = await ctx.send(embed=Embed(title="Setup 1/2", color=self.color,
                                             description="What is your lunch period?\n"
                                                         "Period 5️⃣ starts at 12:15\n"
                                                         "Period 6️⃣ starts at 1:10"))
        for emoji in self.numbers[5:7]:
            await message.add_reaction(emoji)

        def check(r, u):
            return r.emoji in self.numbers and u == ctx.author

        reaction, user = await self.bot.wait_for("reaction_add", check=check)
        user_data["lunch_period"] = self.numbers.index(reaction.emoji)
        print(user_data)

        await message.clear_reactions()

        # Ask the user if they have elective every day
        await message.edit(embed=Embed(title="Setup 2/2", color=self.color,
                                       description="Do you have an elective every day?"))
        for emoji in self.check_x:
            await message.add_reaction(emoji)

        def check_x(r, u):
            return r.emoji in self.check_x and u == ctx.author

        reaction, user = await self.bot.wait_for("reaction_add", check=check_x)
        user_data["every_day"] = reaction.emoji == self.check_x[0]
        print(user_data)

        await message.clear_reactions()
        await message.edit(embed=Embed(title="Setup Complete!", color=Color.green(),
                                       description="You have been registered successfully."))

        file_data[str(ctx.author.id)] = user_data

        with open("user_data.json", "w+") as file:
            json.dump(file_data, file, indent=4)

    @commands.command()
    async def unregister(self, ctx: commands.Context):
        """Unregister yourself from the bot."""
        with open("user_data.json", "r+") as file:
            file_data = json.load(file)

        if str(ctx.author.id) not in file_data:
            await ctx.send(embed=Embed(description="You have not been registered yet! "
                                                   "Do `&register` to register first.", color=Color.red()))
            return

        message = await ctx.send(embed=Embed(title="Are you sure you want to unregister?", color=self.color))

        for emoji in self.check_x:
            await message.add_reaction(emoji)

        def check_x(r, u):
            return r.emoji in self.check_x and u == ctx.author

        reaction, user = await self.bot.wait_for("reaction_add", check=check_x)

        if reaction.emoji == self.check_x[0]:
            file_data.pop(str(ctx.author.id))

            with open("user_data.json", "w+") as file:
                json.dump(file_data, file, indent=4)

            await message.edit(embed=Embed(title="Successfully unregistered!", color=Color.green()))
        else:
            await message.edit(embed=Embed(title="Successfully canceled.", color=Color.red()))

    @commands.command()
    async def view(self, ctx: commands.Context):
        """View your current registration data."""
        with open("user_data.json", "r+") as file:
            file_data = json.load(file)

        if str(ctx.author.id) not in file_data:
            await ctx.send("You have not been registered yet! Do `&register` to register.")
            return

        user_data = file_data[str(ctx.author.id)]
        elective = "with" if user_data['every_day'] else "without"
        embed = Embed(description=f"You are currently registered with your lunch period as "
                                  f"**period {user_data['lunch_period']}** **{elective}** electives every day.",
                      color=self.color)
        embed.set_author(name=f"{ctx.author.display_name}#{ctx.author.discriminator}", icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def toggle(self, ctx: commands.Context):
        self.reminder_enabled = not self.reminder_enabled

        message = "Reminder enabled!" if self.reminder_enabled else "Reminder disabled!"
        await ctx.send(message)

    @tasks.loop(minutes=1.0)
    async def main_loop(self):
        if not self.reminder_enabled:
            return

        now = datetime.now()  # Get's the current time.
        weekday = now.weekday()  # Find the day of the week, needed later.
        now = now.hour * 60 + now.minute - 514  # I used the number of minutes since the first period for calculations.

        if now % 55 == 0 and (weekday not in [5, 6]):  # Makes sure that it's been exactly a period amount of minutes.
            period = now // 55 + 1  # Calculate what period it is.
            print(f"Currently period {period}.")

            # We need the user data of each user, so read from file.
            with open("user_data.json", "r+") as file:
                file_data = json.load(file)

            for user_id, user_data in file_data.items():
                embed = Embed(title="Class starting!",
                              description=f"Period {period} is staring in one minute! Get ready for class!",
                              color=Color.green())

                user = self.bot.get_user(int(user_id))
                elective = 5 if user_data['lunch_period'] == 6 else 6

                if user_data['lunch_period'] == period:  # we don't want to ping on lunch periods
                    pass
                elif elective == period:  # If the period is an elective period...
                    if weekday == 0 or user_data['every_day']:  # Only ping on Mondays, or if they have every day
                        await user.send(embed=embed)
                elif 1 <= period <= 8:
                    await user.send(embed=embed)

    # Makes sure the bot is ready before starting loop
    @main_loop.before_loop
    async def before_main(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.main_loop.cancel()


def setup(bot):
    bot.add_cog(Reminder(bot))
