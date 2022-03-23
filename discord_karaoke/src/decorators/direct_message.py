from discord import DMChannel
from discord.ext import commands


def direct_message():
    def predicate(ctx):
        return type(ctx.channel) is DMChannel

    return commands.check(predicate)
