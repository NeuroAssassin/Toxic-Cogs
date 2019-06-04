from .cooldown import Cooldown


def setup(bot):
    bot.add_cog(Cooldown(bot))
