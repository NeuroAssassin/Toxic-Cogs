from .updatechecker import UpdateChecker
import discord
import asyncio


async def setup(bot):
    owner = bot.get_user(bot.owner_id)
    run_cog_update = False
    cog = UpdateChecker(bot)
    if not (await cog.conf.updated()):
        try:
            await owner.send(
                "Hello!  Thank you for installing this cog.  Please do know however that this cog must know what version your cogs are currently at, so you MUST use `[p]cogupdater all` first in order to get commits.  This command will run `[p]cog update`, then get the latest commits of all your repos.  After running it once however, you should use `[p]cog update`.  The command is disabled after being used once."
            )
        except:
            pass
    bot.add_cog(cog)
