from redbot.core.commands.requires import PrivilegeLevel as PL
from redbot.core.utils.chat_formatting import humanize_number, humanize_list
from redbot.core.commands import commands
from redbot.core.utils import AsyncIter
from collections import Counter
import markdown2
import discord
import random
import re

HUMANIZED_PERMISSIONS = {
    "view": "View server"
}

class DashboardRPC:
    """RPC server handlers for the dashboard to get special things from the bot.
    
    This class contains the basic RPC functions, that don't belong to any other cog"""
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot

        # Initialize RPC handlers
        self.bot.register_rpc_handler(self.get_variables)
        self.bot.register_rpc_handler(self.get_secret)
        self.bot.register_rpc_handler(self.get_commands)
        self.bot.register_rpc_handler(self.get_users_servers)
        self.bot.register_rpc_handler(self.get_server)
        self.bot.register_rpc_handler(self.check_version)

        # To make sure that both RPC server and client are on the same "version"
        self.version = random.randint(1, 10000)

    def unload(self):
        self.bot.unregister_rpc_handler(self.get_variables)
        self.bot.unregister_rpc_handler(self.get_secret)
        self.bot.unregister_rpc_handler(self.get_commands)
        self.bot.unregister_rpc_handler(self.get_users_servers)
        self.bot.unregister_rpc_handler(self.get_server)
        self.bot.unregister_rpc_handler(self.check_version)

    def build_cmd_list(self, cmd_list):
        final = []
        for cmd in cmd_list:
            details = {
                "name": f"{cmd.qualified_name} {cmd.signature}",
                "desc": cmd.short_doc,
                "subs": []
            }
            if isinstance(cmd, commands.Group):
                details['subs'] = self.build_cmd_list(cmd.commands)
            final.append(details)
        return final

    def get_perms(self, guildid, m):
        try:
            role_data = self.cog.cache[guildid]['roles']
        except KeyError:
            return None
        roles = [r.id for r in m.roles]
        perms = []
        for role in role_data:
            if role['roleid'] in roles:
                perms += role['perms']
        return perms

    async def check_version(self, version):
        # Since self.version could possibly be cached, lets do something different
        if self.bot.get_cog("Dashboard") and self.bot.is_ready():
            return {"v": self.bot.get_cog("Dashboard").rpc.version}
        else:
            return {"disconnected": True}

    async def get_variables(self):
        # Because RPC decides to keep this even when unloaded ¯\_(ツ)_/¯
        if self.bot.get_cog("Dashboard") and self.bot.is_ready():
            botinfo = await self.bot._config.custom_info()
            if botinfo is None:
                botinfo = (
                    f"Hello, welcome to the Red Discord Bot dashboard for {self.bot.user.name}! "
                    f"{self.bot.user.name} is based off the popular bot Red Discord Bot, an open source, multifunctional bot. "
                    "It has tons if features including moderation, audio, economy, fun and more! Here, you can control and interact with all these things. "
                    "So what are you waiting for? Invite them now!"
                )
            prefixes = [p for p in await self.bot.get_valid_prefixes() if not re.match(r"<@!?([0-9]+)>", p)]
            count = Counter()
            async for member in AsyncIter(self.bot.get_all_members(), steps=1500):
                count["users"] += 1
                if member.status is not discord.Status.offline:
                    count["onlineusers"] += 1
            returning = {
                'botname': self.bot.user.name,
                'botavatar': str(self.bot.user.avatar_url_as(static_format="png")),
                'botid': self.bot.user.id,
                'botinfo': markdown2.markdown(botinfo),
                'prefix': prefixes,
                'redirect': await self.cog.conf.redirect(),
                'support': await self.cog.conf.support(),
                'servers': humanize_number(len(self.bot.guilds)),
                'users': humanize_number(count['users']),
                'onlineusers': humanize_number(count['onlineusers'])
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
        if self.bot.get_cog("Dashboard") and self.bot.is_ready():
            return {'secret': await self.cog.conf.secret()}
        else:
            return {"disconnected": True}

    async def get_commands(self):
        if self.bot.get_cog("Dashboard") and self.bot.is_ready():
            returning = []
            for name, cog in self.bot.cogs.items():
                stripped = []
                for c in cog.__cog_commands__:
                    if not c.parent:
                        stripped.append(c)
                returning.append({
                    "name": name,
                    "desc": cog.__doc__,
                    "cmds": self.build_cmd_list(stripped)
                })
            returning = sorted(returning, key=lambda k: k['name'])
            return returning
        else:
            return {"disconnected": True}

    async def get_users_servers(self, userid):
        if self.bot.get_cog("Dashboard") and self.bot.is_ready():
            guilds = []
            is_owner = False
            try:
                if await self.bot.is_owner(self.bot.get_user(userid)):
                    is_owner = True
            except AttributeError:
                # Bot doesn't even find user using bot.get_user, might as well spare all the data processing and return
                return []

            # This could take a while
            async for guild in AsyncIter(self.bot.guilds, steps=1300):
                sgd = {
                    "name": guild.name,
                    "id": str(guild.id),
                    "owner": str(guild.owner),
                    "icon": str(guild.icon_url_as(format="png"))[:-13] or "https://cdn.discordapp.com/embed/avatars/1",
                    "animated": guild.is_icon_animated(),
                    "go": False
                }
                if is_owner:
                    guilds.append(sgd)
                    continue

                m = guild.get_member(userid)
                if not m:
                    continue

                if guild.owner.id == userid:
                    guilds.append(sgd)
                    continue

                perms = self.get_perms(guild.id, m)
                if perms is None:
                    continue

                if 'view' in perms:
                    guilds.append(sgd)
                    continue

                # User doesn't have view permission
            return guilds
        else:
            return {"disconnected": True}

    async def get_server(self, userid, serverid):
        if self.bot.get_cog("Dashboard") and self.bot.is_ready():
            guild = self.bot.get_guild(serverid)
            if not guild:
                return {"status": 0}

            user = guild.get_member(userid)
            baseuser = self.bot.get_user(userid)
            is_owner = False
            if await self.bot.is_owner(baseuser):
                is_owner = True

            if not user:
                if not baseuser and not is_owner:
                    return {"status": 0}

            if is_owner:
                humanized = ['Everything (Bot Owner)']
                joined = None
            elif guild.owner.id == userid:
                humanized = ["Everything (Guild Owner)"]
                joined = user.joined_at.strftime("%B %d, %Y")
            else:
                perms = self.get_perms(serverid, user)
                if perms is None or 'view' not in perms:
                    return {"status": 0}

                humanized = []
                for p in perms:
                    humanized.append(HUMANIZED_PERMISSIONS[p])

                joined = user.joined_at.strftime("%B %d, %Y")

            stats = {
                "o": 0,
                "i": 0,
                "d": 0,
                "f": 0
            }

            for m in guild.members:
                if m.status is discord.Status.online:
                    stats['o'] += 1
                elif m.status is discord.Status.idle:
                    stats['i'] += 1
                elif m.status is discord.Status.dnd:
                    stats['d'] += 1
                elif m.status is discord.Status.offline:
                    stats['f'] += 1

            if guild.verification_level is discord.VerificationLevel.none:
                vl = "None"
            elif guild.verification_level is discord.VerificationLevel.low:
                vl = "1 - Low"
            elif guild.verification_level is discord.VerificationLevel.medium:
                vl = "2 - Medium"
            elif guild.verification_level is discord.VerificationLevel.high:
                vl = "3 - High"
            elif guild.verification_level is discord.VerificationLevel.extreme:
                vl = "4 - Extreme"

            parts = guild.region.name.split("_")
            for i, p in enumerate(parts):
                if p in ["eu", "us", "vip"]:
                    parts[i] = p.upper()
                else:
                    parts[i] = p.title()
            region = " ".join(parts)

            if serverid not in self.cog.cache:
                warn = True
            else:
                warn = False

            guild_data = {
                "status": 1,
                "name": guild.name,
                "id": guild.id,
                "owner": str(guild.owner),
                "icon": str(guild.icon_url_as(format="png"))[:-13] or "https://cdn.discordapp.com/embed/avatars/1",
                "animated": guild.is_icon_animated(),
                "members": humanize_number(len(guild.members)),
                "online": humanize_number(stats['o']),
                "idle": humanize_number(stats['i']),
                "dnd": humanize_number(stats['d']),
                "offline": humanize_number(stats['f']),
                "bots": humanize_number(len([user for user in guild.members if user.bot])),
                "humans": humanize_number(len([user for user in guild.members if not user.bot])),
                "perms": humanize_list(humanized),
                "created": guild.created_at.strftime("%B %d, %Y"),
                "joined": joined,
                "roleswarn": warn,
                "vl": vl,
                "region": region
            }

            return guild_data
        else:
            return {"disconnected": True}