from .cooldown import Cooldown


async def setup(bot):
    await bot.add_cog(Cooldown(bot))
