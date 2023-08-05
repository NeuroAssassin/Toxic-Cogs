from redbot.core.bot import Red

from .dashboard import Dashboard


async def setup(bot: Red):
    cog = Dashboard(bot)
    await bot.add_cog(cog)
    await cog.initialize()
