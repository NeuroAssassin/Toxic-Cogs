from .authgg import AuthGG


async def setup(bot):
    await bot.add_cog(AuthGG(bot))
