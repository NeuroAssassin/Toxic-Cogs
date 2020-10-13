from redbot.core.bot import Red
from redbot.core.commands import commands

from .utils import rpccheck


class DashboardRPC_Webhooks:
    def __init__(self, cog: commands.Cog):
        self.bot: Red = cog.bot
        self.cog: commands.Cog = cog

        self.bot.register_rpc_handler(self.webhook_receive)

    def unload(self):
        self.bot.unregister_rpc_handler(self.webhook_receive)

    @rpccheck()
    async def webhook_receive(self, payload: dict) -> dict:
        self.bot.dispatch("webhook_receive", payload)
        return {"status": 1}
