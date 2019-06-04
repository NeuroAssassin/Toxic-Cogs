from .deleter import Deleter


def setup(bot):
    bot.add_cog(Deleter(bot))
