from .concurrency import Concurrency


def setup(bot):
    bot.add_cog(Concurrency(bot))
