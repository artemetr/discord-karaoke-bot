from typing import List

from discord.ext import commands


def allowed_guilds(guild_ids: List[int]):
    def predicate(ctx):
        return ctx.guild.id in guild_ids

    return commands.check(predicate)
