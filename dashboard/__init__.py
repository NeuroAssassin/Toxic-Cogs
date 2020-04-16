from .dashboard import Dashboard


async def setup(bot):
    cog = Dashboard(bot)
    bot.add_cog(cog)
