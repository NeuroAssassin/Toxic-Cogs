from .simon import Simon


def setup(bot):
    bot.add_cog(Simon(bot))
