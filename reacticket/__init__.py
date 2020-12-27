from .reacticket import ReacTicket


def setup(bot):
    bot.add_cog(ReacTicket(bot))
