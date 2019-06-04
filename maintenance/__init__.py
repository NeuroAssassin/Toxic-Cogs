from .maintenance import Maintenance


async def setup(bot):
    cog = Maintenance(bot)
    bot.add_cog(cog)
