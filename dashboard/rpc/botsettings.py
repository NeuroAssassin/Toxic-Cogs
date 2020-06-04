class DashboardRPC_BotSettings:
    def __init__(self, cog):
        self.bot = cog.bot
        self.cog = cog

        # Initialize RPC handlers
        self.bot.register_rpc_handler(self.serverprefix)
        self.bot.register_rpc_handler(self.adminroles)
        self.bot.register_rpc_handler(self.modroles)

    def unload(self):
        self.bot.unregister_rpc_handler(self.serverprefix)
        self.bot.unregister_rpc_handler(self.adminroles)
        self.bot.unregister_rpc_handler(self.modroles)

    async def serverprefix(self, guildid, userid, method = "get", prefixes = []):
        if self.bot.get_cog("Dashboard") and self.bot.is_ready():
            if not (guild := self.bot.get_guild(int(guildid))):
                return {"status": 0, "message": "Unknown guild"}

            m = guild.get_member(userid)
            if not m:
                return {"status": 0, "message": "Unknown guild"}
            
            perms = self.cog.rpc.get_perms(guildid, m)
            if (perms is None or "botsettings" not in perms) and (userid != guild.owner_id):
                return {"status": 0, "message": "Unknown guild"}

            method = method.lower()
            if method == "get":
                return {"prefixes": await self.bot.get_valid_prefixes(guild)}
            elif method == "set":
                method = getattr(self.bot, "set_prefixes", self.bot._prefix_cache.set_prefixes)
                await method(guild=guild, prefixes=prefixes)
                return {'status': 1}
        else:
            return {"disconnected": True}

    async def adminroles(self, guildid, userid, method = "get", roles = []):
        if self.bot.get_cog("Dashboard") and self.bot.is_ready():
            roles = list(map(int, roles))
            if not (guild := self.bot.get_guild(int(guildid))):
                return {"status": 0, "message": "Unknown guild"}

            m = guild.get_member(userid)
            if not m:
                return {"status": 0, "message": "Unknown guild"}
            
            perms = self.cog.rpc.get_perms(guildid, m)
            if (perms is None or "botsettings" not in perms) and (userid != guild.owner_id):
                return {"status": 0, "message": "Unknown guild"}

            method = method.lower()
            if method == "get":
                return {"roles": await self.bot._config.guild(guild).admin_role()}
            elif method == "set":
                for r in roles:
                    rl = guild.get_role(r)
                    if not rl:
                        return {"status": 0, "message": f"Role ID {r} not found"}
                await self.bot._config.guild(guild).admin_role.set(roles)
                return {'status': 1}
        else:
            return {"disconnected": True}

    async def modroles(self, guildid, userid, method = "get", roles = []):
        if self.bot.get_cog("Dashboard") and self.bot.is_ready():
            roles = list(map(int, roles))
            if not (guild := self.bot.get_guild(int(guildid))):
                return {"status": 0, "message": "Unknown guild"}

            m = guild.get_member(userid)
            if not m:
                return {"status": 0, "message": "Unknown guild"}
            
            perms = self.cog.rpc.get_perms(guildid, m)
            if (perms is None or "botsettings" not in perms) and (userid != guild.owner_id):
                return {"status": 0, "message": "Unknown guild"}

            method = method.lower()
            if method == "get":
                return {"roles": await self.bot._config.guild(guild).mod_role()}
            elif method == "set":
                for r in roles:
                    rl = guild.get_role(r)
                    if not rl:
                        return {"status": 0, "message": f"Role ID {r} not found"}
                await self.bot._config.guild(guild).mod_role.set(roles)
                return {'status': 1}
        else:
            return {"disconnected": True}