from redbot.core.bot import Red
from redbot.core import commands, checks, Config
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import box, humanize_list
from collections import defaultdict
import discord
import traceback
import asyncio
import subprocess
import sys

from .baserpc import DashboardRPC

HUMANIZED_PERMISSIONS = {"view": "View server"}


class Dashboard(commands.Cog):

    __version__ = "0.0.7a"

    def __init__(self, bot: Red):
        self.bot = bot

        self.config = Config.get_conf(self, identifier=473541068378341376)
        self.config.register_global(
            secret="",
            redirect="http://127.0.0.1:42356",
            owner_perm=15,
            widgets=[],
            testwidgets=[],
            support="",
        )
        self.config.register_guild(roles=[])
        self.configcache = defaultdict(self.cache_defaults)

        self.rpc = DashboardRPC(self)

    def cog_unload(self):
        self.configcache.clear()
        self.rpc.unload()

    def cache_defaults(self):
        return {"roles": []}

    async def initialize(self):
        config = await self.config.all_guilds()
        for k, v in config.items():
            self.configcache[k] = v

    @commands.group()
    async def dashboard(self, ctx: commands.Context):
        """Group command for controlling the web dashboard for Red"""

    @checks.guildowner()
    @dashboard.group()
    async def roles(self, ctx: commands.Context):
        """Customize the roles that have permission to certain parts of the dashboard"""

    @roles.command()
    async def create(self, ctx: commands.Context, role: discord.Role, *permissions):
        """Register a new discord role to access certain parts of the dashboard"""
        roles = await self.config.guild(ctx.guild).roles()
        if role.id in [r["roleid"] for r in roles]:
            await ctx.send(
                f"That role is already registered.  Please edit with `{ctx.prefix}dashboard roles edit`."
            )
            return
        assigning = []
        missing = []
        for p in permissions:
            if p in HUMANIZED_PERMISSIONS:
                assigning.append(p)
            else:
                missing.append(p)
        if assigning:
            async with self.config.guild(ctx.guild).roles() as data:
                data.append({"roleid": role.id, "perms": assigning})
            self.configcache[ctx.guild.id]["roles"] = {"roleid": role.id, "perms": assigning}
        else:
            await ctx.send("Failed to identify any permissions in list.  Please try again.")
            return

        await ctx.send(
            f"Role registered.\n**Permissions assigned**: {humanize_list(assigning)}\n"
            f"**Permissions unidentified**: {humanize_list(missing or ['None'])}"
        )

    @roles.command()
    async def edit(self, ctx: commands.Context, role: discord.Role, *permissions):
        """Edit the permissions registered with a registered role"""
        changing = []
        missing = []
        for p in permissions:
            if p in HUMANIZED_PERMISSIONS:
                changing.append(p)
            else:
                missing.append(f"`{p}`")

        if not changing:
            await ctx.send("Failed to identify any permissions in list. Please try again.")
            return

        roles = await self.config.guild(ctx.guild).roles()
        try:
            ro = [ro for ro in roles if ro["roleid"] == role.id][0]
        except IndexError:
            return await ctx.send("That role is not registered")

        del roles[roles.index(ro)]

        added = []
        removed = []
        for p in changing:
            if p in ro["perms"]:
                ro["perms"].remove(p)
                removed.append(p)
            else:
                ro["perms"].append(p)
                added.append(p)

        if not ro["perms"]:
            await ctx.send(
                f"Failed to edit role. If you wish to remove all permissions from the role, please use `{ctx.clean_prefix}dashboard roles delete`."
            )
            return

        roles.append(ro)
        await self.config.guild(ctx.guild).roles.set(roles)
        self.configcache[ctx.guild.id]["roles"] = roles

        await ctx.send(
            "Successfully edited role.\n"
            f"**Added**: {humanize_list(added or ['None'])}\n"
            f"**Removed**: {humanize_list(removed or ['None'])}\n"
            f"**Unidentified**: {humanize_list(missing or ['None'])}"
        )

    @roles.command()
    async def delete(self, ctx: commands.Context, *, role: discord.Role):
        """Unregister a role from the dashboard"""
        roles = await self.config.guild(ctx.guild).roles()
        try:
            ro = [ro for ro in roles if ro["roleid"] == role.id][0]
        except IndexError:
            return await ctx.send("That role is not registered")

        del roles[roles.index(ro)]
        await self.config.guild(ctx.guild).roles.set(roles)
        self.configcache[ctx.guild.id]["roles"] = roles

        await ctx.send("Successfully deleted role.")

    @roles.command()
    async def list(self, ctx: commands.Context):
        """List roles registered with dashboard"""
        data = await self.config.guild(ctx.guild).roles()
        roles = [
            ctx.guild.get_role(role["roleid"]).mention
            for role in data
            if ctx.guild.get_role(role["roleid"])
        ]
        if not roles:
            return await ctx.send("No roles set.")
        e = discord.Embed(title="Registered roles", description="\n".join(roles), color=0x0000FF)
        await ctx.send(embed=e)

    @roles.command()
    async def info(self, ctx: commands.Context, *, role: discord.Role):
        """List permissions for a registered role"""
        roles = await self.config.guild(ctx.guild).roles()
        try:
            r = [ro for ro in roles if ro["roleid"] == role.id][0]
        except IndexError:
            return await ctx.send("That role is not registered")

        humanized = [HUMANIZED_PERMISSIONS[perm] for perm in r["perms"]]

        e = discord.Embed(description=f"**Role {role.mention} permissions**\n", color=0x0000FF)
        e.description += humanize_list(humanized)

        await ctx.send(embed=e)

    @roles.command()
    async def perms(self, ctx: commands.Context):
        """Displays permission keywords matched with humanized descriptions"""
        msg = [f"{key}: {value}" for key, value in HUMANIZED_PERMISSIONS.items()]
        await ctx.send("\n".join(msg))

    @checks.is_owner()
    @dashboard.group()
    async def settings(self, ctx: commands.Context):
        """Group command for setting up the web dashboard for this Red bot"""

    @settings.command()
    async def support(self, ctx: commands.Context, url: str = ""):
        """Set the URL for support.  This is recommended to be a Discord Invite.

        Leaving it blank will remove it.
        """
        await self.config.support.set(url)
        await ctx.tick()

    @settings.group()
    async def oauth(self, ctx: commands.Context):
        """Group command for changing the settings related to Discord OAuth."""

    @oauth.command()
    async def secret(self, ctx: commands.Context, *, secret: str):
        """Set the client secret needed for Discord Oauth."""
        await self.config.secret.set(secret)
        await ctx.tick()

    @oauth.command()
    async def redirect(self, ctx: commands.Context, redirect: str):
        """Set the redirect for after logging in via Discord OAuth."""
        await self.config.redirect.set(redirect)
        await ctx.tick()

    @settings.command()
    async def view(self, ctx: commands.Context):
        """View the current dashboard settings."""
        redirect = await self.config.redirect()
        if ctx.guild:
            secret = "[REDACTED]"
            if not ("127.0.0.1" in redirect or "localhost" in redirect or "192.168" in redirect):
                redirect = "[REDACTED]"
        else:
            secret = await self.config.secret()
        if not secret:
            secret = "[Not set]"
        support = await self.config.support()
        description = (
            f"Client Secret:         |  {secret}\n"
            f"Redirect URI:          |  {redirect}\n"
            f"Support Server:        |  {support}"
        )
        embed = discord.Embed(title="Red V3 Dashboard Settings", color=0x0000FF)
        embed.description = box(description, lang="ini")
        embed.add_field(name="Dashboard Version", value=box(f"[{self.__version__}]", lang="ini"))
        embed.set_footer(text="Dashboard created by Neuro Assassin")
        await ctx.send(embed=embed)
