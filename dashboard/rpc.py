from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.commands import commands
import discord
import markdown2

class DashboardRPC:
    """RPC server handlers for the dashboard to get special things from the bot"""
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot

        # Initialize RPC handlers
        self.bot.register_rpc_handler(self.get_variables)
        self.bot.register_rpc_handler(self.get_secret)
        self.bot.register_rpc_handler(self.get_commands)

    def unload(self):
        self.bot.unregister_rpc_handler(self.get_variables)
        self.bot.unregister_rpc_handler(self.get_secret)
        self.bot.unregister_rpc_handler(self.get_commands)

    def build_cmd_list(self, cmd_list):
        final = []
        for cmd in cmd_list:
            details = {
                "name": f"{cmd.qualified_name} {cmd.signature}",
                "desc": cmd.short_doc,
                "subs": []
            }
            if isinstance(cmd, commands.Group):
                details['subs'] = self.build_cmd_list(cmd.all_commands.values())
            final.append(details)
        return final

    async def get_variables(self):
        # Because RPC decides to keep this even when unloaded ¯\_(ツ)_/¯
        if self.bot.get_cog("Dashboard"):
            botinfo = await self.bot._config.custom_info()
            if botinfo is None:
                botinfo = f"Hello, welcome to the Red Discord Bot dashboard for {self.bot.user.name}!  {self.bot.user.name} is based off the popular bot Red Discord Bot, an open source, multifunctional bot.  It has tons if features including moderation, audio, economy, fun and more!  Here, you can control and interact with all these things.  So what are you waiting for?  Invite them now!"
            returning = {
                'botname': self.bot.user.name,
                'botavatar': str(self.bot.user.avatar_url),
                'botid': self.bot.user.id,
                'botinfo': markdown2.markdown(botinfo),
                'prefix': (await self.bot.get_valid_prefixes())[0],
                'redirect': await self.cog.conf.redirect(),
                'support': await self.cog.conf.support(),
                'servers': humanize_number(len(self.bot.guilds)),
                'users': humanize_number(len([member for member in self.bot.get_all_members()])),
                'onlineusers': humanize_number(len([user for user in self.bot.get_all_members() if user.status is not discord.Status.offline]))
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

    async def get_commands(self):
        if self.bot.get_cog("Dashboard"):
            returning = {}
            for name, cog in self.bot.cogs.items():
                stripped = []
                for c in cog.__cog_commands__:
                    if not c.parent:
                        stripped.append(c)
                returning[name] = self.build_cmd_list(stripped)
            new = {}
            for key in sorted(returning.keys()):
                new[key] = returning[key]
            return new
        else:
            return {"disconnected": True}