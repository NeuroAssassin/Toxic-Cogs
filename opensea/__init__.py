from .opensea import OpenSea


def setup(bot):
    bot.add_cog(OpenSea(bot))
