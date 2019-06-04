from .switcher import Switcher


def setup(bot):
    bot.add_cog(Switcher(bot))
