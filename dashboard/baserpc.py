from datetime import datetime
from typing import List
from html import escape
import random
import re

import discord
import markdown2
from redbot.core.bot import Red
from redbot.core.commands import commands
from redbot.core.commands.requires import PrivilegeLevel
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_list, humanize_number, humanize_timedelta

from .rpc.alias import DashboardRPC_AliasCC
from .rpc.botsettings import DashboardRPC_BotSettings
from .rpc.permissions import DashboardRPC_Permissions
from .rpc.utils import rpccheck
from .rpc.webhooks import DashboardRPC_Webhooks

HUMANIZED_PERMISSIONS = {
    "view": "View server on dashboard",
    "botsettings": "Customize guild-specific settings on dashboard",
    "permissions": "Customize guild-specific permissions to commands",
    #    "aliascc": "Customize guild-specific command aliases and custom commands",
}


class DashboardRPC:
    """RPC server handlers for the dashboard to get special things from the bot.

    This class contains the basic RPC functions, that don't belong to any other cog"""

    def __init__(self, cog: commands.Cog):
        self.cog: commands.Cog = cog
        self.bot: Red = cog.bot

        # Initialize RPC handlers
        self.bot.register_rpc_handler(self.get_variables)
        self.bot.register_rpc_handler(self.get_secret)
        self.bot.register_rpc_handler(self.get_commands)
        self.bot.register_rpc_handler(self.get_users_servers)
        self.bot.register_rpc_handler(self.get_server)
        self.bot.register_rpc_handler(self.check_version)
        self.bot.register_rpc_handler(self.notify_owners_of_blacklist)

        # RPC Extensions
        self.extensions = []
        self.extensions.append(DashboardRPC_BotSettings(self.cog))
        self.extensions.append(DashboardRPC_Permissions(self.cog))
        self.extensions.append(DashboardRPC_AliasCC(self.cog))
        self.extensions.append(DashboardRPC_Webhooks(self.cog))

        # To make sure that both RPC server and client are on the same "version"
        self.version = random.randint(1, 10000)

        # Caches; you can thank trusty for the cog info one
        self.cog_info_cache = {}
        self.invite_url = None
        self.owner = None

    def unload(self):
        self.bot.unregister_rpc_handler(self.get_variables)
        self.bot.unregister_rpc_handler(self.get_secret)
        self.bot.unregister_rpc_handler(self.get_commands)
        self.bot.unregister_rpc_handler(self.get_users_servers)
        self.bot.unregister_rpc_handler(self.get_server)
        self.bot.unregister_rpc_handler(self.check_version)
        self.bot.unregister_rpc_handler(self.notify_owners_of_blacklist)

        for extension in self.extensions:
            extension.unload()

    async def build_cmd_list(self, cmd_list: List[commands.Command], details=True, do_escape=True):
        final = []
        async for cmd in AsyncIter(cmd_list):
            if details:
                if cmd.hidden:
                    continue
                if cmd.requires.privilege_level == PrivilegeLevel.BOT_OWNER:
                    continue
                try:
                    if do_escape:
                        details = {
                            "name": escape(f"{cmd.qualified_name} {cmd.signature}"),
                            "desc": escape(cmd.short_doc or ""),
                            "subs": [],
                        }
                    else:
                        details = {
                            "name": f"{cmd.qualified_name} {cmd.signature}",
                            "desc": cmd.short_doc or "",
                            "subs": [],
                        }
                except ValueError:
                    continue
                if isinstance(cmd, commands.Group):
                    details["subs"] = await self.build_cmd_list(cmd.commands, do_escape=do_escape)
                final.append(details)
            else:
                if cmd.requires.privilege_level == PrivilegeLevel.BOT_OWNER:
                    continue
                final.append(escape(cmd.qualified_name) if do_escape else cmd.qualified_name)
                if isinstance(cmd, commands.Group):
                    final += await self.build_cmd_list(
                        cmd.commands, details=False, do_escape=do_escape
                    )
        return final

    def get_perms(self, guildid: int, m: discord.Member):
        try:
            role_data = self.cog.configcache[int(guildid)]["roles"]
        except KeyError:
            return None
        roles = [r.id for r in m.roles]
        perms = []
        for role in role_data:
            if role["roleid"] in roles:
                perms += [p for p in role["perms"] if p not in perms]
        return perms

    @rpccheck()
    async def check_version(self):
        return {"v": self.bot.get_cog("Dashboard").rpc.version}

    async def notify_owners_of_blacklist(self, ip):
        async with self.cog.config.blacklisted() as data:
            data.append(ip)
        await self.bot.send_to_owners(
            f"[Dashboard] Detected suspicious activity from IP {ip}.  They have been blacklisted."
        )

    @rpccheck()
    async def get_variables(self):
        botinfo = await self.bot._config.custom_info()
        if botinfo is None:
            botinfo = (
                f"Hello, welcome to the Red Discord Bot dashboard for {self.bot.user.name}! "
                f"{self.bot.user.name} is based off the popular bot Red Discord Bot, an open "
                "source, multifunctional bot. It has tons of features including moderation, "
                "audio, economy, fun and more! Here, you can control and interact with "
                f"{self.bot.user.name}'s settings. So what are you waiting for? Invite them now!"
            )

        prefixes = [
            p for p in await self.bot.get_valid_prefixes() if not re.match(r"<@!?([0-9]+)>", p)
        ]

        count = len(self.bot.users)

        if self.invite_url is None:
            core = self.bot.get_cog("Core")
            self.invite_url = await core._invite_url()

        delta = datetime.utcnow() - self.bot.uptime
        uptime_str = humanize_timedelta(timedelta=delta)

        data = await self.cog.config.all()
        client_id = data["clientid"] or self.bot.user.id

        returning = {
            "botname": self.bot.user.name,
            "botavatar": str(self.bot.user.avatar_url_as(static_format="png")),
            "botid": self.bot.user.id,
            "clientid": client_id,
            "botinfo": markdown2.markdown(botinfo),
            "prefix": prefixes,
            "redirect": data["redirect"],
            "support": data["support"],
            "color": data["defaultcolor"],
            "servers": humanize_number(len(self.bot.guilds)),
            "users": humanize_number(count),
            "blacklisted": data["blacklisted"],
            "uptime": uptime_str,
            "invite": self.invite_url,
            "meta": data["meta"],
        }
        if self.owner is None:
            app_info = await self.bot.application_info()
            if app_info.team:
                self.owner = str(app_info.team.name)
            else:
                self.owner = str(app_info.owner)

        returning["owner"] = self.owner
        return returning

    @rpccheck()
    async def get_secret(self):
        return {"secret": await self.cog.config.secret()}

    @rpccheck()
    async def get_commands(self):
        returning = []
        downloader = self.bot.get_cog("Downloader")
        for name, cog in self.bot.cogs.copy().items():
            stripped = []

            for c in cog.__cog_commands__:
                if not c.parent:
                    stripped.append(c)

            cmds = await self.build_cmd_list(stripped, do_escape=False)
            if not cmds:
                continue

            author = "Unknown"
            repo = "Unknown"
            # Taken from Trusty's downloader fuckery,
            # https://gist.github.com/TrustyJAID/784c8c32dd45b1cc8155ed42c0c56591
            if name not in self.cog_info_cache:
                if downloader:
                    module = downloader.cog_name_from_instance(cog)
                    installed, cog_info = await downloader.is_installed(module)
                    if installed:
                        author = humanize_list(cog_info.author) if cog_info.author else "Unknown"
                        try:
                            repo = (
                                cog_info.repo.clean_url if cog_info.repo.clean_url else "Unknown"
                            )
                        except AttributeError:
                            repo = "Unknown (Removed from Downloader)"
                    elif cog.__module__.startswith("redbot."):
                        author = "Cog Creators"
                        repo = "https://github.com/Cog-Creators/Red-DiscordBot"
                    self.cog_info_cache[name] = {}
                    self.cog_info_cache[name]["author"] = author
                    self.cog_info_cache[name]["repo"] = repo
            else:
                author = self.cog_info_cache[name]["author"]
                repo = self.cog_info_cache[name]["repo"]

            returning.append(
                {
                    "name": escape(name or ""),
                    "desc": escape(cog.__doc__ or ""),
                    "cmds": cmds,
                    "author": escape(author or ""),
                    "repo": repo,
                }
            )
        returning = sorted(returning, key=lambda k: k["name"])
        return returning

    @rpccheck()
    async def get_users_servers(self, userid: int):
        userid = int(userid)
        guilds = []
        is_owner = False
        try:
            if await self.bot.is_owner(self.bot.get_user(userid)):
                is_owner = True
        except AttributeError:
            # Bot doesn't even find user using bot.get_user,
            # might as well spare all the data processing and return
            return []

        # This could take a while
        async for guild in AsyncIter(self.bot.guilds, steps=1300):
            sgd = {
                "name": escape(guild.name),
                "id": str(guild.id),
                "owner": escape(str(guild.owner)),
                "icon": str(guild.icon_url_as(format="png"))[:-13]
                or "https://cdn.discordapp.com/embed/avatars/1.",
                "animated": guild.is_icon_animated(),
                "go": False,
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

            if "view" in perms:
                guilds.append(sgd)
                continue

            # User doesn't have view permission
        return guilds

    @rpccheck()
    async def get_server(self, userid: int, serverid: int):
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
            humanized = ["Everything (Bot Owner)"]
            perms = []
            joined = None

        if guild.owner.id == userid:
            humanized = ["Everything (Guild Owner)"]
            perms = list(HUMANIZED_PERMISSIONS.keys())
            joined = user.joined_at.strftime("%B %d, %Y")
        else:
            if user:
                perms = self.get_perms(serverid, user)
                joined = user.joined_at.strftime("%B %d, %Y")
            else:
                perms = []
                joined = "Not a part of this guild"
            if (perms is None or "view" not in perms) and not is_owner:
                return {"status": 0}

            humanized = [perm.title() for perm in perms] or ["None"]

        stats = {"o": 0, "i": 0, "d": 0, "f": 0}

        for m in guild.members:
            if m.status is discord.Status.online:
                stats["o"] += 1
            elif m.status is discord.Status.idle:
                stats["i"] += 1
            elif m.status is discord.Status.dnd:
                stats["d"] += 1
            elif m.status is discord.Status.offline:
                stats["f"] += 1

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
        else:
            vl = "Unknown"

        region = getattr(guild.region, "name", guild.region)
        parts = region.split("_")
        for i, p in enumerate(parts):
            if p in ["eu", "us", "vip"]:
                parts[i] = p.upper()
            else:
                parts[i] = p.title()
        region = " ".join(parts)

        if not self.cog.configcache.get(serverid, {"roles": []})["roles"]:
            warn = True
        else:
            warn = False

        adminroles = []
        ar = await self.bot._config.guild(guild).admin_role()
        for rid in ar:
            r = guild.get_role(rid)
            if r:
                adminroles.append((rid, r.name))

        modroles = []
        mr = await self.bot._config.guild(guild).mod_role()
        for rid in mr:
            r = guild.get_role(rid)
            if r:
                modroles.append((rid, r.name))

        all_roles = [(r.id, r.name) for r in guild.roles]

        guild_data = {
            "status": 1,
            "name": escape(guild.name),
            "id": guild.id,
            "owner": escape(str(guild.owner)),
            "icon": str(guild.icon_url_as(format="png"))[:-13]
            or "https://cdn.discordapp.com/embed/avatars/1.",
            "animated": guild.is_icon_animated(),
            "members": humanize_number(len(guild.members)),
            "online": humanize_number(stats["o"]),
            "idle": humanize_number(stats["i"]),
            "dnd": humanize_number(stats["d"]),
            "offline": humanize_number(stats["f"]),
            "bots": humanize_number(len([user for user in guild.members if user.bot])),
            "humans": humanize_number(len([user for user in guild.members if not user.bot])),
            "perms": humanize_list(humanized),
            "permslist": perms,
            "created": guild.created_at.strftime("%B %d, %Y"),
            "joined": joined,
            "roleswarn": warn,
            "vl": vl,
            "region": region,
            "prefixes": await self.bot.get_valid_prefixes(guild),
            "adminroles": adminroles,
            "modroles": modroles,
            "roles": all_roles,
        }

        return guild_data
