# Thanks to El Laggron (who copied this from Red) in his instantcmd cog, from whom I copied this code

from .sql import Sql
import logging
import asyncio

from redbot.core.data_manager import cog_data_path
from .loggers import Log

log = logging.getLogger("neuro.sql")
# this should be called after initializing the logger


async def ask_enable_sentry(bot):
    owner = bot.get_user(bot.owner_id)

    def check(message):
        return message.author == owner and message.channel == owner.dm_channel

    if not owner.bot:  # make sure the owner is set
        await owner.send(
            "Hello there!  Thanks for choosing to install my `sql` cog.  Howeverm because this cog is quite complex, there is a way built in to the cog that allows for errors to be reported to me.  However, this is completely optional.  Would you like it enabled? (Type 'yes' to enable or anything else to disable/deny)."
        )
        try:
            message = await bot.wait_for("message", timeout=60, check=check)
        except asyncio.TimeoutError:
            await owner.send(
                "Requested timed out.  Due to no response, settings have been set so that error reporting is **NOT** occuring, and the will not be reported to the owner.  You can change this at any time with `[p]sql internal`."
            )
            return None
        if "yes" in message.content.lower():
            await owner.send(
                "Thanks for enabling the error reporting!\n"
                "At any time, you can disable this by using the `[p]sql internal` command."
            )
            log.info("Sentry error reporting was enabled for this instance.")
            return True
        else:
            await owner.send(
                "The error logging was not enabled. You can change that by "
                "using the `[p]sql internal` command."
            )
            return False

async def setup(bot):
    cog = Sql(bot)
    sentry = Log(bot, cog.__version__)
    sentry.enable_stdout()
    cog._set_log(sentry)
    if await cog.data.enable_sentry() is None:
        response = await ask_enable_sentry(bot)
        await cog.data.enable_sentry.set(response)
    if await cog.data.enable_sentry():
        cog.sentry.enable()
    bot.add_cog(cog)