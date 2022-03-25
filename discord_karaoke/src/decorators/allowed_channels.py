from typing import List

from discord.ext import commands


def allowed_channels(channel_ids: List[int] = None, channel_names: List[str] = None):
    def predicate(ctx):
        if channel_ids:
            return ctx.channel.id in channel_ids
        elif channel_names:
            return ctx.channel.name in channel_names
        else:
            return False

    return commands.check(predicate)
