from .evolution import Evolution
from redbot.core import bank


async def setup(bot):
    is_global = await bank.is_global()
    if not is_global:
        raise RuntimeError("Bank must be global for this cog to work.")
    bot.add_cog(Evolution(bot))
