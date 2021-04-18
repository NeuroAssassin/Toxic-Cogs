from .esolang import Esolang


def setup(bot):
    bot.add_cog(Esolang(bot))
