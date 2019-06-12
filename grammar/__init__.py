from .grammar import Grammar


def setup(bot):
    bot.add_cog(Grammar(bot))
