import base64
import json
import os
import random
from datetime import timedelta
from glob import glob
from io import BytesIO
from typing import Optional, Union

import discord
from discord.ext import commands, tasks
from mutagen import File
from mutagen.flac import FLAC, Picture

from ..lang import send_embed
from ..main import ClientData, FunBot


def connect_ensure_voice():
    """Same as ensure_voice but instead allows the bot to join if not already connected
    Internally calls the join command"""

    async def predicate(ctx: commands.Context):
        return await ctx.invoke(ctx.bot.get_command('join'))

    return commands.check(predicate)


def ensure_voice():
    """Only allows the command to be executed when the bot is connected to a voice channel"""

    async def predicate(ctx: commands.Context):
        if ctx.voice_client is None:
            await send_embed(ctx, "music.error.bot_not_connected", prefix=ctx.prefix)
            return False
        return True

    return commands.check(predicate)


def dir_list() -> set: return set(x[6:-1].lower() for x in glob("music/*/"))


def timedelta_to_str(time: timedelta) -> str:
    output = str(time).split(':', 1)[1]
    if output[0] == '0':
        output = output[1:]

    return output


def create_bar(current_time: timedelta, total_time: timedelta) -> str:
    str_current_time = timedelta_to_str(current_time)
    str_total_time = timedelta_to_str(total_time)

    start = round(current_time / total_time * 30)
    bar = '▬' * start + '🔘' + '▬' * (29 - start)

    return f'`{str_current_time} {bar} {str_total_time}`'


async def update_bar(client_data: ClientData) -> None:
    if not client_data.message:
        return

    embed: discord.Embed = client_data.message.embeds[0]
    index = len(embed.fields) - 1

    file_ = File(client_data.now_playing)
    total_length = timedelta(seconds=file_.info.length//1)

    new_bar = create_bar(client_data.timestamp, total_length)
    embed.set_field_at(index, name="** **", value=new_bar)

    try:
        await client_data.message.edit(embed=embed)
    except discord.NotFound:
        pass


def set_if_exists(embed: discord.Embed, name: str, value: Union[list[str], str, float], inline=True) -> None:
    if not value:
        return

    if isinstance(value, list):
        value = value[0]

    embed.add_field(name=name, value=value, inline=inline)


def get_art(file_) -> tuple[Picture, str]:
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
        picture = Picture(base64.b64decode(b64_data))
        ext = extensions.get(picture.mime, "jpg")

    return picture, ext


def load_cache() -> dict[str, str]:
    if not os.path.exists('cache.json'):
        return {}

    with open('cache.json', 'r') as file:
        return json.load(file)


def save_cache(cache: dict[str, str]) -> None:
    with open('cache.json', 'w+') as file:
        json.dump(cache, file, indent=4)


class Music(commands.Cog):
    def __init__(self, bot: FunBot):
        self.bot = bot

        self.bar_update_loop.start()
        self.music_loop.start()
        self.music_data = self.bot.music_data

        self.cache_channel: discord.TextChannel = self.bot.get_channel(self.bot.config['Bot']['cache_channel'])
        self.cache = load_cache()

    @commands.command(aliases=['j'])
    async def join(self, ctx: commands.Context) -> bool:
        """Make the bot join a voice channel to start playing music!"""

        if ctx.author.voice:
            if not ctx.voice_client:
                await ctx.author.voice.channel.connect()
            elif ctx.author.voice.channel == ctx.voice_client.channel:
                if ctx.message.content.split()[0].lower().strip() in ('&join', '&j'):
                    await send_embed(ctx, "music.error.bot_already_connected")
                return True
            else:
                await ctx.voice_client.disconnect()
                await ctx.author.voice.channel.connect()

            await send_embed(ctx, 'music.join')
            self.music_data[ctx.guild.id].channel = ctx.channel
            return True
        else:
            await send_embed(ctx, "music.error.user_not_connected")
            return False

    @ensure_voice()
    @commands.command(aliases=['stop', 'l'])
    async def leave(self, ctx: commands.Context):
        """Disconnects the bot from the voice channel and clears the queue."""

        await ctx.voice_client.disconnect()
        self.music_data.pop(ctx.guild.id)  # remove the data for this isntance

        await send_embed(ctx, 'music.leave')

    @commands.command(aliases=['ls'])
    async def list(self, ctx: commands.Context):
        """Lists all the possible song groups that you can add to the queue."""

        await send_embed(ctx, 'music.list', groups=sorted(dir_list()))

    @connect_ensure_voice()
    @commands.command(aliases=['p'])
    async def play(self, ctx: commands.Context, *groups: str):
        """Plays the specified song group or resumes the bot when paused."""

        if ctx.voice_client.is_paused():
            await self.resume(ctx)
            return

        if not groups:
            await send_embed(ctx, 'music.error.no_arg', arg="play")
            return

        queue = self.music_data[ctx.guild.id].queue
        added = []
        invalid = []
        already_queued = []

        for group in groups:
            group = group.lower()

            if group in queue:
                already_queued.append(group)
            elif group in dir_list():
                queue.add(group)
                added.append(group)
            else:
                invalid.append(group)

        if invalid:
            await send_embed(ctx, 'music.error.queue_fail', groups=invalid)
        if already_queued:
            await send_embed(ctx, 'music.error.already_queued', groups=already_queued)
        if added:
            await send_embed(ctx, 'music.queued', groups=added)

    @connect_ensure_voice()
    @commands.command(name='playall', aliases=['pa'])
    async def play_all(self, ctx: commands.Context):
        """Adds all song groups to the queue"""

        self.music_data[ctx.guild.id].queue = dir_list()
        await send_embed(ctx, 'music.queued', groups=dir_list())

    @ensure_voice()
    @commands.command()
    async def pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if ctx.voice_client.is_paused():
            await send_embed(ctx, 'music.error.already_paused')
        else:
            ctx.voice_client.pause()
            await send_embed(ctx, 'music.pause')

    @ensure_voice()
    @commands.command()
    async def resume(self, ctx: commands.Context):
        """Resumes the currently playing song."""

        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await send_embed(ctx, 'music.resume')
        else:
            await send_embed(ctx, 'music.error.already_playing')

    @ensure_voice()
    @commands.command(aliases=['s'])
    async def skip(self, ctx: commands.Context):
        """Skips the current song."""

        # stopping the client makes the task think that a song has finished
        ctx.voice_client.stop()
        await send_embed(ctx, 'music.skipped')

    @ensure_voice()
    @commands.command(aliases=['r', 'rm'])
    async def remove(self, ctx: commands.Context, *groups: str):
        """Removes a group from the queue"""

        if not groups:
            await send_embed(ctx, 'music.error.no_arg', arg="remove")
            return

        queue = self.music_data[ctx.guild.id].queue
        removed = []
        invalid = []

        for group in groups:
            group = group.lower()

            if group in queue:
                queue.remove(group)
                removed.append(group)
            else:
                invalid.append(group)

        if invalid:
            await send_embed(ctx, 'music.error.remove_fail', groups=invalid)
        if removed:
            await send_embed(ctx, 'music.removed', groups=removed)

    @ensure_voice()
    @commands.command(aliases=['cl', 'clr'])
    async def clear(self, ctx: commands.Context):
        """Clears the queue."""

        self.music_data[ctx.guild.id].queue = set()
        await send_embed(ctx, 'music.clear')

    @ensure_voice()
    @commands.command(name='nowplaying', aliases=['np'])
    async def now_playing(self, ctx: commands.Context):
        """Displays the currently playing song."""

        path = self.music_data[ctx.guild.id].now_playing
        timestamp = self.music_data[ctx.guild.id].timestamp

        if not path:
            await send_embed(ctx, 'music.error.nothing_playing', prefix=ctx.prefix)
            return

        embed = await self.make_np_embed(path, timestamp)
        await ctx.send(embed=embed)

    async def make_np_embed(self, path: str, timestamp: timedelta) -> discord.Embed:
        file_ = File(path)

        total_length = timedelta(seconds=file_.info.length//1)

        title = file_.get('title', path)
        if isinstance(title, list):
            title = title[0]

        embed = discord.Embed(title=title, colour=discord.Colour.random())

        set_if_exists(embed, name='Artist', value=file_.get('artist'))
        set_if_exists(embed, name='Album', value=file_.get('album'))
        set_if_exists(embed, name='Track', value=file_.get('tracknumber'))

        embed.add_field(name='** **', value=create_bar(timestamp, total_length))
        embed.set_thumbnail(url=await self.get_cache_url(path))

        return embed

    async def get_cache_url(self, path: str) -> Optional[str]:
        if path in self.cache:
            return self.cache[path]

        file_ = File(path)
        picture, ext = get_art(file_)

        if picture:
            file = discord.File(BytesIO(picture.data), filename=f'cover.{ext}')
            message: discord.Message = await self.cache_channel.send(file=file)
            self.cache[path] = message.attachments[0].url
        else:
            self.cache[path] = None

        save_cache(self.cache)
        return self.cache[path]

    @commands.is_owner()
    @commands.command()
    async def populate_cache(self, ctx: commands.Context):
        """Admin-only command to populate the cache."""

        songs = [song for group in dir_list() for song in glob(f'music/{group}/*')]
        urls = [await self.get_cache_url(song) for song in songs]
        await ctx.send(len(urls))

    @ensure_voice()
    @commands.command(aliases=['q'])
    async def queue(self, ctx: commands.Context):
        """Displays the current groups in the queue"""

        queue = sorted(self.music_data[ctx.guild.id].queue)
        if queue:
            await send_embed(ctx, 'music.queue', groups=queue)
        else:
            await send_embed(ctx, 'music.queue_empty')

    @tasks.loop(seconds=1)
    async def music_loop(self):
        for client in self.bot.voice_clients:
            client_data = self.music_data[client.guild.id]

            if client.is_playing():
                client_data.timestamp += timedelta(seconds=1)
                continue

            if client.is_paused():
                continue

            if not client_data.queue:
                client_data.now_playing = None
                continue

            # Get a list of all the possible songs to play
            groups = [glob(f"music/{group}/*") for group in client_data.queue]
            songs = [song for group in groups for song in group]

            # prevent the current song from being played twice in a row
            if client_data.now_playing in songs:
                songs.remove(client_data.now_playing)

            client_data.now_playing = random.choice(songs)

            source = discord.FFmpegPCMAudio(client_data.now_playing)
            client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

            # Reset the timestamp
            client_data.timestamp = timedelta()

            # Send a np message for the song that just started playing
            embed = await self.make_np_embed(client_data.now_playing, client_data.timestamp)

            if client_data.message:
                await client_data.message.delete()

            client_data.message = await client_data.channel.send(embed=embed)

    @tasks.loop(seconds=5)
    async def bar_update_loop(self):
        for client in self.bot.voice_clients:
            if not client.is_playing():
                continue

            client_data = self.music_data[client.guild.id]

            await update_bar(client_data)

    @music_loop.before_loop
    @bar_update_loop.before_loop
    async def before_music(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Music(bot))
