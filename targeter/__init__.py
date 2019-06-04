from .targeter import Targeter


def setup(bot):
    bot.add_cog(Targeter(bot))
