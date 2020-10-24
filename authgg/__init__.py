from .authgg import AuthGG


def setup(bot):
    bot.add_cog(AuthGG(bot))
