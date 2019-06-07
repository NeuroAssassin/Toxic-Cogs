from .updatechecker import UpdateChecker


def setup(bot):
    bot.add_cog(UpdateChecker(bot))
