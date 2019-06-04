from .minesweeper import Minesweeper


def setup(bot):
    bot.add_cog(Minesweeper(bot))
