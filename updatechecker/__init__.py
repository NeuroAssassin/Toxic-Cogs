from .updatechecker import UpdateChecker
import discord
import asyncio

async def setup(bot):
    owner = bot.get_user(bot.owner_id)
    run_cog_update = False
    cog = UpdateChecker(bot)
    if not (await cog.conf.updated()):
        try:
            await owner.send("Hello!  Thank you for installing this cog.  Please do know however that this cog must get the latest commits from all the latest repos in order to keep track, so for this cog to function properly, please run `[p]update all` instead of `[p]cog update.`  This will still end up calling that command, but then it will track down the commits and save them to know when updates are available.")
        except:
            pass
    bot.add_cog(cog)