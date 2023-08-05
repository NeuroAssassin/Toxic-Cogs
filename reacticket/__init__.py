from .reacticket import ReacTicket


async def setup(bot):
    await bot.add_cog(ReacTicket(bot))
