import discord
from redbot.core.bot import Red
from redbot.core.commands import commands

from .utils import permcheck, rpccheck


class DashboardRPC_BotSettings:
    def __init__(self, cog: commands.Cog):
        self.bot: Red = cog.bot
        self.cog: commands.Cog = cog

        # Initialize RPC handlers
        self.bot.register_rpc_handler(self.serverprefix)
        self.bot.register_rpc_handler(self.adminroles)
        self.bot.register_rpc_handler(self.modroles)

    def unload(self):
        self.bot.unregister_rpc_handler(self.serverprefix)
        self.bot.unregister_rpc_handler(self.adminroles)
        self.bot.unregister_rpc_handler(self.modroles)

    @rpccheck()
    @permcheck(permissions=["botsettings"])
    async def serverprefix(
        self, guild: discord.Guild, member: discord.Member, method: str = "get", prefixes=None
    ):
        if prefixes is None:
            prefixes = []
        method = method.lower()
        if method == "get":
            return {"prefixes": await self.bot.get_valid_prefixes(guild)}
        elif method == "set":
            method = getattr(self.bot, "set_prefixes", self.bot._prefix_cache.set_prefixes)
            await method(guild=guild, prefixes=prefixes)
            return {"status": 1}

    @rpccheck()
    @permcheck(permissions=["botsettings"])
    async def adminroles(
        self, guild: discord.Guild, member: discord.Member, method: str = "get", roles=None
    ):
        if roles is None:
            roles = []
        roles = list(map(int, roles))

        method = method.lower()
        if method == "get":
            return {"roles": await self.bot._config.guild(guild).admin_role()}
        elif method == "set":
            for r in roles:
                rl = guild.get_role(r)
                if not rl:
                    return {"status": 0, "message": f"Role ID {r} not found"}
            await self.bot._config.guild(guild).admin_role.set(roles)
            return {"status": 1}

    @rpccheck()
    @permcheck(permissions=["botsettings"])
    async def modroles(
        self, guild: discord.Guild, member: discord.Member, method: str = "get", roles=None
    ):
        if roles is None:
            roles = []
        roles = list(map(int, roles))

        method = method.lower()
        if method == "get":
            return {"roles": await self.bot._config.guild(guild).mod_role()}
        elif method == "set":
            for r in roles:
                rl = guild.get_role(r)
                if not rl:
                    return {"status": 0, "message": f"Role ID {r} not found"}
            await self.bot._config.guild(guild).mod_role.set(roles)
            return {"status": 1}
