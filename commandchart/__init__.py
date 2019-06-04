from .commandchart import CommandChart


def setup(bot):
    bot.add_cog(CommandChart(bot))
