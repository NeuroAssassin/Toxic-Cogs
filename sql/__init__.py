from .sql import Sql

def setup(bot):
    bot.add_cog(Sql(bot))