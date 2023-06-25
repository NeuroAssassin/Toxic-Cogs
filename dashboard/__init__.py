import inspect

from redbot.core.bot import Red

from .dashboard import Dashboard


async def setup(bot: Red):
    cog = Dashboard(bot)
    if inspect.iscoroutinefunction(bot.add_cog):
        await bot.add_cog(cog)
    else:
        bot.add_cog(cog)
    await cog.initialize()
