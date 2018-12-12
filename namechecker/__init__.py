from .namechecker import NameChecker

def setup(bot):
    bot.add_cog(NameChecker(bot))