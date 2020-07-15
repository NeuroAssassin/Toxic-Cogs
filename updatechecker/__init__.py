from .updatechecker import UpdateChecker
import discord
import asyncio


async def setup(bot):
    cog = UpdateChecker(bot)
    bot.add_cog(cog)
