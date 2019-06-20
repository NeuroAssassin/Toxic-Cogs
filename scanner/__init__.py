from .scanner import Scanner


def setup(bot):
    bot.add_cog(Scanner(bot))
