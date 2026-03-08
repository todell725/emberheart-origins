"""
Channel routing decorators for EmberHeart: Origins
Ported from Claudes-EmberHeart
"""
import discord
from discord.ext import commands
import logging

logger = logging.getLogger("EH_Routing")

class ChannelRoutingError(commands.CheckFailure):
    pass

def require_channel(channel_name: str):
    """
    A gentle check/redirect decorator.
    Instead of preventing the command, we allow it but give the Cog
    a `ctx.target_channel` attribute if it needs to redirect output.
    """
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author) and "bypass" in ctx.message.content.lower():
            ctx.target_channel = ctx.channel
            return True

        if not getattr(ctx, "guild", None):
            ctx.target_channel = ctx.channel
            return True

        target = discord.utils.get(ctx.guild.channels, name=channel_name)

        if not target:
            logger.warning(f"Required channel #{channel_name} not found in guild {ctx.guild.name}.")
            ctx.target_channel = ctx.channel
        else:
            ctx.target_channel = target

        if ctx.channel.id != ctx.target_channel.id:
            pass

        return True

    return commands.check(predicate)

def require_channel_strict(channel_name: str):
    """
    A strict check decorator. Fails the command if not run in the specific channel.
    """
    async def predicate(ctx):
        if ctx.channel.name == channel_name:
            return True
        raise ChannelRoutingError(f"Command must be used in #{channel_name}.")
    return commands.check(predicate)
