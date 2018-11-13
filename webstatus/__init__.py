from .webstatus import Webstatus

def setup(bot):
    bot.add_cog(Webstatus(bot))