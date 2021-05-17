import re
from typing import Union

import discord
from yaml import safe_load


def dotted_access_dict(input_dict: dict, keys: Union[str, list]):
    if isinstance(keys, str):
        keys = keys.split('.')

    if len(keys) == 1:
        return input_dict.get(keys[0], input_dict)
    else:
        return dotted_access_dict(input_dict[keys[0]], keys[1:])


def get_highest_color(input_dict: dict, key: str):
    color = dotted_access_dict(input_dict, key).get('color')

    if color:
        return color

    return get_highest_color(input_dict, str(re.match(r'.*(?=\.)', key)))


def color_to_discord(name: str) -> discord.Color:
    try:
        color = getattr(discord.Color, name.lower())()
    except AttributeError:
        color = discord.Color.default()

    return color


async def send_embed(messageable: discord.abc.Messageable, key: str, **kwargs) -> discord.Message:
    with open('bot/lang.yaml', 'r') as file:
        all_data = safe_load(file)

    data = dotted_access_dict(all_data, key)

    # Convert the color stored in the yaml file to a discord.Color
    color = color_to_discord(get_highest_color(all_data, key))

    description = data.get('description', key + '.description')
    title = data.get('title', '')

    # Dynamic values are stored as %{value}, replace those with the given values
    for placeholder, value in kwargs.items():
        if placeholder == 'groups':
            value = '`, `'.join(value)

        description = description.replace(f'%{{{placeholder}}}', str(value))
        title = title.replace(f'%{{{placeholder}}}', str(value))

    embed = discord.Embed(title=title, description=description, color=color)
    return await messageable.send(embed=embed)
