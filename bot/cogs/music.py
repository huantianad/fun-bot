import base64
import random
from datetime import timedelta
from glob import glob
from io import BytesIO

import discord
from discord.ext import commands, tasks
from mutagen import File
from mutagen.flac import FLAC, Picture


def connect_ensure_voice():
    async def predicate(ctx: commands.Context):
        return await ctx.invoke(ctx.bot.get_command('join'))

    return commands.check(predicate)


def ensure_voice():
    """Only allows the command to be executed when the bot is connected to a voice channel"""

    async def predicate(ctx: commands.Context):
        if ctx.voice_client is None:
            await ctx.send(f"I'm not connected to a voice channel yet! Use `{ctx.prefix}join` to add me.")
            return False
        return True

    return commands.check(predicate)


def dir_list(): return set(x[6:-1].lower() for x in glob("music/*/"))


def set_if_exists(embed, name, value, inline=True):
    if not value:
        return

    if isinstance(value, list):
        value = value[0]
    elif isinstance(value, float):
        value = str(timedelta(seconds=value//1)).split(':', 1)[1]

    embed.add_field(name=name, value=value, inline=inline)


def get_art(file_):
    extensions = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
    }

    picture = None

    if isinstance(file_, FLAC):
        picture = file_.pictures[0]
        ext = extensions.get(picture.mime, "jpg")
        return picture, ext

    for b64_data in file_.get("metadata_block_picture", []):
        data = base64.b64decode(b64_data)
        picture = Picture(data)
        ext = extensions.get(picture.mime, "jpg")

    return picture, ext


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.music_loop.start()
        self.music_data = self.bot.music_data

    @commands.command(aliases=['j'])
    async def join(self, ctx: commands.Context):
        """Make the bot join a voice channel to start playing music!"""

        if ctx.author.voice:
            if not ctx.voice_client:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.voice_client.disconnect()
                await ctx.author.voice.channel.connect()

            await ctx.send("Hello! :wave:")
            self.music_data[ctx.guild.id]['channel'] = ctx.channel
            return True
        else:
            await ctx.send("You are not connected to a voice channel.")
            return False

    @ensure_voice()
    @commands.command(aliases=['stop'])
    async def leave(self, ctx: commands.Context):
        """Disconnects the bot from the voice channel and clears the queue."""

        await ctx.voice_client.disconnect()
        self.music_data.pop(ctx.guild.id)  # remove the data for this isntance

        await ctx.send("Goodbye :wave:")

    @ensure_voice()
    @commands.command(aliases=['ls'])
    async def list(self, ctx: commands.Context):
        """Lists all the possible song groups that you can add to the queue."""

        await ctx.send(f"Possible song groups: `{'`, `'.join(dir_list())}`")

    @connect_ensure_voice()
    @commands.command(aliases=['p'])
    async def play(self, ctx: commands.Context, *groups):
        """Plays the specified song group or resumes the bot when paused."""
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resumed playing :arrow_forward:")
            return

        queue = self.music_data[ctx.guild.id]['queue']
        invalid = []

        for group in groups:
            group = group.lower()

            if group in dir_list():
                queue.add(group)
            else:
                invalid.append(group)

        if invalid:
            await ctx.send(f"Failed to add `{'`, `'.join(invalid)}`")
        if queue:
            await ctx.send(f"The queue now contains: `{'`, `'.join(queue)}`")

    @connect_ensure_voice()
    @commands.command(name='playall', aliases=['pa'])
    async def play_all(self, ctx: commands.Context):
        """Adds all song groups to the queue"""

        self.music_data[ctx.guild.id]['queue'] = dir_list()
        await ctx.send(f"The queue now contains: `{'`, `'.join(dir_list())}`")

    @ensure_voice()
    @commands.command()
    async def pause(self, ctx: commands.Context):
        """Pauses the music."""

        if ctx.voice_client.is_paused():
            await ctx.send("I'm already paused!")
        else:
            ctx.voice_client.pause()
            await ctx.send("Paused :pause_button:")

    @ensure_voice()
    @commands.command()
    async def resume(self, ctx: commands.Context):
        """Resumes the music if paused."""

        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resumed playing :arrow_forward:")
        else:
            await ctx.send("I'm already playing!")

    @ensure_voice()
    @commands.command(aliases=['s'])
    async def skip(self, ctx: commands.Context):
        """Skips the current song."""

        # stopping the playing makes the task think that a song has finished
        ctx.voice_client.stop()
        await ctx.send('Skipped!')

    @ensure_voice()
    @commands.command(aliases=['r'])
    async def remove(self, ctx: commands.Context, *groups):
        """Removes a group from the queue"""

        queue = self.music_data[ctx.guild.id]['queue']
        invalid = []

        for group in groups:
            try:
                queue.remove(group)
            except ValueError:
                invalid.append(group)

        if invalid:
            await ctx.send(f"Failed to remove `{', '.join(invalid)}`.")
        if queue:
            await ctx.send(f"The queue now contains: `{', '.join(queue)}`.")
        else:
            await ctx.send("The queue is empty.")

    @ensure_voice()
    @commands.command(aliases=['cl', 'clr'])
    async def clear(self, ctx: commands.Context):
        """Clears the queue."""

        self.music_data[ctx.guild.id]['queue'] = set()
        await ctx.send("The queue has been cleared!")

    @ensure_voice()
    @commands.command(name='nowplaying', aliases=['np'])
    async def now_playing(self, ctx: commands.Context):
        """Displays the currently playing song."""

        path = self.music_data[ctx.guild.id]['now_playing']

        if not path:
            await ctx.send(f"Looks like nothing's playing right now. Use `{ctx.prefix}play` to play something.")
            return

        async with ctx.typing():
            embed, image = await self.make_np_embed(path)

            if image is not None:
                await ctx.send(embed=embed, file=image)
            else:
                await ctx.send(embed=embed)

    async def make_np_embed(self, path):
        file_ = File(path)

        embed = discord.Embed(title=file_.get('title', path)[0], colour=discord.Colour.random())

        set_if_exists(embed, name='Artist', value=file_.get('artist'))
        set_if_exists(embed, name='Album', value=file_.get('album'))
        embed.add_field(name='** **', value='** **')

        set_if_exists(embed, name='Track', value=file_.get('tracknumber'))
        set_if_exists(embed, name='Duration', value=file_.info.length)
        embed.add_field(name='** **', value='** **')

        set_if_exists(embed, name='Description', value=file_.get('description'))
        set_if_exists(embed, name='Comment', value=file_.get('comment'))

        picture, ext = get_art(file_)

        if picture is not None:
            image = discord.File(BytesIO(picture.data), filename=f'cover.{ext}')
            embed.set_thumbnail(url=f'attachment://cover.{ext}')
        else:
            image = None

        return embed, image

    @ensure_voice()
    @commands.command(aliases=['q'])
    async def queue(self, ctx: commands.Context):
        """Displays the current groups in the queue"""

        queue = self.music_data[ctx.guild.id]['queue']
        message = f"The queue contains: `{'`, `'.join(queue)}`." if queue else "The queue is empty."
        await ctx.send(message)

    @tasks.loop(seconds=1)
    async def music_loop(self):
        for client in self.bot.voice_clients:
            client_data = self.music_data[client.guild.id]

            if client.is_playing() or client.is_paused():
                continue

            if not client_data['queue']:
                client_data['now_playing'] = None
                continue

            # Get a list of all the possible songs to play
            groups = [glob(f"music/{group}/*") for group in client_data['queue']]
            songs = [song for group in groups for song in group]

            # prevent the current song from being played twice in a row
            if client_data['now_playing'] in songs:
                songs.remove(client_data['now_playing'])

            client_data['now_playing'] = random.choice(songs)

            source = discord.FFmpegPCMAudio(client_data['now_playing'])
            client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

            # Show song that was just played
            channel = client_data['channel']  # type: discord.TextChannel
            message = client_data['message']  # type: discord.Message

            async with channel.typing():

                embed, image = await self.make_np_embed(client_data['now_playing'])

                if message:
                    await message.delete()

                if image is not None:
                    client_data['message'] = await channel.send(embed=embed, file=image)
                else:
                    client_data['message'] = await channel.send(embed=embed)

    @music_loop.before_loop
    async def before_music(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Music(bot))
