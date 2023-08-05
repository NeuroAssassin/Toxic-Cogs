from redbot.core.bot import Red
from redbot.core.commands import commands

from .utils import rpccheck


class DashboardRPC_OAuth:
    def __init__(self, cog: commands.Cog):
        self.bot: Red = cog.bot
        self.cog: commands.Cog = cog

        self.bot.register_rpc_handler(self.oauth_receive)

    def unload(self):
        self.bot.unregister_rpc_handler(self.oauth_receive)

    @rpccheck()
    async def oauth_receive(self, user_id: int, payload: dict) -> dict:
        self.bot.dispatch("oauth_receive", user_id, payload)
        return {"status": 1}
