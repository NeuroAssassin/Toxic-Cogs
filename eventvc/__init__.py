from .eventvc import EventVC


def setup(bot):
    bot.add_cog(EventVC(bot))
