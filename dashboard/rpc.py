import discord

class DashboardRPC:
    """RPC server handlers for the dashboard to get special things from the bot"""
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot

        # Initialize RPC handlers
        self.bot.register_rpc_handler(self.get_variables)
        self.bot.register_rpc_handler(self.get_secret)

    def unload(self):
        self.bot.unregister_rpc_handler(self.get_variables)
        self.bot.unregister_rpc_handler(self.get_secret)

    async def get_variables(self):
        # Because RPC decides to keep this even when unloaded ¯\_(ツ)_/¯
        if self.bot.get_cog("Dashboard"):
            returning = {
                'botname': self.bot.user.name,
                'botavatar': str(self.bot.user.avatar_url),
                'botid': self.bot.user.id,
                'botinfo': await self.bot._config.custom_info(),
                'redirect': await self.cog.conf.redirect(),
                'support': await self.cog.conf.support(),
                'servers': len(self.bot.guilds),
                'users': len([member for member in self.bot.get_all_members()]),
                'onlineusers': len([user for user in self.bot.get_all_members() if user.status is not discord.Status.offline])
            }
            app_info = await self.bot.application_info()
            if app_info.team:
                returning['owner'] = str(app_info.team.name)
            else:
                returning['owner'] = str(app_info.owner)
            return returning
        else:
            return {"disconnected": True}

    async def get_secret(self):
        return {'secret': await self.cog.conf.secret()}