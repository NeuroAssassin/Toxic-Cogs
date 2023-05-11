from .maintenance import Maintenance

__red_end_user_data_statement__ = (
    "This cog stores user's Discord IDs for operational data, in the form of "
    "whitelist to specify what users may interact with the cog/bot.  This data "
    "is only deleted on Discord's user deletion requests."
)


async def setup(bot):
    cog = Maintenance(bot)
    await bot.add_cog(cog)
