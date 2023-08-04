from .opensea import OpenSea


async def setup(bot):
    await bot.add_cog(OpenSea(bot))
