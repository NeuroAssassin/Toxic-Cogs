from .sql import Sql


async def setup(bot):
    bot.add_cog(Sql(bot))
