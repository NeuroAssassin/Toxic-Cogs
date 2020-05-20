from .deleter import Deleter


def setup(bot):
    cog = Deleter(bot)
    bot.add_cog(cog)