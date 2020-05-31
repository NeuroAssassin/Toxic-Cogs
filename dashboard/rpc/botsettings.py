class DashboardRPC_BotSettings:
    def __init__(self, cog):
        self.bot = cog.bot
        self.cog = cog

        # Initialize RPC handlers
        self.bot.register_rpc_handler(self.serverprefix)

    def unload(self):
        self.bot.unregister_rpc_handler(self.serverprefix)

    async def serverprefix(self, guildid, userid, method = "get", prefixes = []):
        if self.bot.get_cog("Dashboard") and self.bot.is_ready():
            if not (guild := self.bot.get_guild(int(guildid))):
                return {"status": 0, "msg": "Unknown guild"}

            m = guild.get_member(userid)
            if not m:
                return {"status": 0, "msg": "Unknown guild"}
            
            perms = self.cog.rpc.get_perms(guildid, m)
            if (perms is None or "botsettings" not in perms) and (userid != guild.owner_id):
                return {"status": 0, "msg": "Unknown guild"}

            method = method.lower()
            if method == "get":
                return {"prefixes": await self.bot.get_valid_prefixes(guild)}
            elif method == "set":
                method = getattr(self.bot, "set_prefixes", self.bot._prefix_cache.set_prefixes)
                await method(guild=guild, prefixes=prefixes)
                return {'status': 1}
        else:
            return {"disconnected": True}