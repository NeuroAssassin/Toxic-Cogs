from redbot.core import commands, checks, Config
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import humanize_list
import discord
import traceback
import asyncio
import subprocess
import sys

from .baserpc import DashboardRPC

HUMANIZED_PERMISSIONS = {
    "view": "View server",
}

class Dashboard(commands.Cog):

    __version__ = "0.0.6a"

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=473541068378341376)
        self.conf.register_global(
            secret="",
            redirect="http://127.0.0.1:42356",
            owner_perm=15,
            widgets=[],
            testwidgets=[],
            support="",
        )
        self.conf.register_guild(
            roles=[]
        )
        self.rpc = DashboardRPC(self)

        self.cache = {}

        self.task = self.bot.loop.create_task(self.update_perm_cache())

    def cog_unload(self):
        self.rpc.unload()

    async def update_perm_cache(self):
        await self.bot.wait_until_ready()
        self.cache = await self.conf.all_guilds()

    def get_guild_roles(self, guildid):
        try:
            return self.cache[guildid]['roles']
        except KeyError:
            self.cache[guildid] = {"roles": []}
            return []

    @commands.group()
    async def dashboard(self, ctx):
        """Group command for controlling the web dashboard for Red"""
        pass

    @checks.guildowner()
    @dashboard.group()
    async def roles(self, ctx):
        """Customize the roles that have permission to certain parts of the dashboard"""
        pass

    @roles.command()
    async def create(self, ctx, role: discord.Role, *permissions):
        """Register a new discord role to access certain parts of the dashboard"""
        roles = self.get_guild_roles(ctx.guild.id)
        if role.id in [r['roleid'] for r in roles]:
            await ctx.send(f"That role is already registered.  Please edit with `{ctx.prefix}dashboard roles edit`.")
            return
        assigning = []
        missing = []
        for p in permissions:
            if p in HUMANIZED_PERMISSIONS:
                assigning.append(p)
            else:
                missing.append(p)
        if assigning:
            self.cache[ctx.guild.id]['roles'].append({
                "roleid": role.id,
                "perms": assigning
            })
            await self.conf.guild(ctx.guild).roles.set(self.cache[ctx.guild.id]['roles'])
        else:
            await ctx.send("Failed to identify any permissions in list.  Please try again.")
            return

        if not missing:
            missing = "None"
        else:
            missing = humanize_list(missing)
        
        await ctx.send(f"Role registered.\n**Permissions assigned**: {humanize_list(assigning)}\n**Permissions unidentified**: {missing}")

    @roles.command()
    async def edit(self, ctx, role: discord.Role, *permissions):
        """Edit the permissions registered with a regisetered role"""
        changing = []
        missing = []
        for p in permissions:
            if p in HUMANIZED_PERMISSIONS:
                changing.append(p)
            else:
                missing.append(f"`{p}`")

        if not changing:
            await ctx.send("Failed to identify any permissions in list.  Please try again.")
            return

        roles = self.get_guild_roles(ctx.guild.id)
        ro = None
        for r in roles:
            if r['roleid'] == role.id:
                ro = r
        if ro is None:
            await ctx.send("That role is not regisetered.")
            return

        del roles[roles.index(ro)]

        added = []
        removed = []
        for p in changing:
            if p in ro['perms']:
                ro['perms'].remove(p)
                removed.append(p)
            else:
                ro['perms'].append(p)
                added.append(p)

        if ro['perms'] == []:
            await ctx.send(f"Failed to edit role.  If you wish to remove all permissions from the role, please use `{ctx.prefix}dashboard roles delete`.")
            return

        roles.append(ro)
        self.cache[ctx.guild.id]['roles'] = roles
        await self.conf.guild(ctx.guild).roles.set(self.cache[ctx.guild.id]['roles'])

        if missing == []:
            missing = "None"
        else:
            missing = humanize_list(missing)

        if added == []:
            added = "None"
        else:
            added = humanize_list(added)

        if removed == []:
            removed = "None"
        else:
            removed = humanize_list(removed)

        await ctx.send(f"Successfully edited role.\n**Added**: {added}\n**Removed**: {removed}\n**Unidentified**: {missing}")

    @roles.command()
    async def delete(self, ctx, *, role: discord.Role):
        """Unregister a role from the dashboard"""
        roles = self.get_guild_roles(ctx.guild.id)
        ro = None
        for r in roles:
            if r['roleid'] == role.id:
                ro = r
        if not ro:
            await ctx.send("That role is not registered")
            return

        del roles[roles.index(ro)]
        self.cache[ctx.guild.id]['roles'] = roles
        await self.conf.guild(ctx.guild).roles.set(self.cache[ctx.guild.id]['roles'])

        await ctx.send("Successfully deleted role.")

    @roles.command()
    async def list(self, ctx):
        """List roles registered with dashboard"""
        roles = self.get_guild_roles(ctx.guild.id)
        e = discord.Embed(title="Registered roles", color=0x0000FF)
        e.description = ""
        for r in roles:
            r = ctx.guild.get_role(r['roleid'])
            if r:
                e.description += f"{r.mention}\n"
        if e.description == "":
            e.description = "No roles set."
        await ctx.send(embed=e)

    @roles.command()
    async def info(self, ctx, *, role: discord.Role):
        """List permissions for a registered role"""
        roles = self.get_guild_roles(ctx.guild.id)
        try:
            r = [ro for ro in roles if ro['roleid'] == role.id][0]
        except IndexError:
            await ctx.send("That role is not registered")
            return

        humanized = []
        for p in r['perms']:
            humanized.append(HUMANIZED_PERMISSIONS[p])

        e = discord.Embed(description=f"**Role {role.mention} permissions**\n", color=0x0000FF)
        e.description += humanize_list(humanized)

        await ctx.send(embed=e)

    @roles.command()
    async def perms(self, ctx):
        """Displays permission keywords matched with humanized descriptions"""
        sending = ""
        for key, value in HUMANIZED_PERMISSIONS.items():
            sending += f"{key}: {value}\n"
        await ctx.send(sending)

    @checks.is_owner()
    @dashboard.group()
    async def settings(self, ctx):
        """Group command for setting up the web dashboard for this Red bot"""
        pass

    @settings.command()
    async def support(self, ctx, url: str = ""):
        """Set the URL for support.  This is recommended to be a Discord Invite.

        Leaving it blank will remove it."""
        await self.conf.support.set(url)
        await ctx.tick()

    @settings.group()
    async def oauth(self, ctx):
        """Group command for changing the settings related to Discord OAuth."""
        pass

    @oauth.command()
    async def secret(self, ctx, *, secret: str):
        """Set the client secret needed for Discord Oauth."""
        await self.conf.secret.set(secret)
        await ctx.tick()

    @oauth.command()
    async def redirect(self, ctx, redirect: str):
        """Set the redirect for after logging in via Discord OAuth."""
        await self.conf.redirect.set(redirect)
        await ctx.tick()

    @settings.command()
    async def view(self, ctx):
        """View the current dashboard settings."""
        embed = discord.Embed(title="Red V3 Dashboard Settings", color=0x0000FF)
        redirect = await self.conf.redirect()
        if ctx.guild:
            secret = "[REDACTED]"
            if not ("127.0.0.1" in redirect or "localhost" in redirect or "192.168" in redirect):
                redirect = "[REDACTED]"
        else:
            secret =  await self.conf.secret()
        if not secret:
            secret = "[Not set]"
        support = await self.conf.support()
        description = (
            f"Client Secret:         |  {secret}\n"
            f"Redirect URI:          |  {redirect}\n"
            f"Support Server:        |  {support}"
        )
        embed.description = "```ini\n" + description + "```"
        embed.add_field(name="Dashboard Version", value=f"```ini\n[{self.__version__}]```")
        embed.set_footer(text="Dashboard created by Neuro Assassin")
        await ctx.send(embed=embed)
