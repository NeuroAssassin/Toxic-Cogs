from . import bank

from .evolution import Evolution

__red_end_user_data_statement__ = (
    "This cog stores user's Discord IDs for the sake of storing game data. "
    "Users may delete their own data at the cost of losing game data through "
    "a data request, if the bot is configured to lose data at the cost of "
    "functionality.  Alternatively, there is a in-cog command to delete user "
    "data as well."
)


async def setup(bot):
    bank._init(bot)
    is_global = await bank.is_global()
    if not is_global:
        raise RuntimeError("Bank must be global for this cog to work.")
    cog = Evolution(bot)
    await bot.add_cog(cog)
    await cog.utils.initialize()
