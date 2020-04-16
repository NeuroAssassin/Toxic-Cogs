from redbot.core import commands, checks, Config
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
import discord
import traceback
import asyncio
import subprocess
import sys

from .rpc import DashboardRPC


class Dashboard(commands.Cog):

    __version__ = "0.0.2a"

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
        self.path = bundled_data_path(self)
        self.rpc = DashboardRPC(self)

    def cog_unload(self):
        self.rpc.unload()

    @commands.group()
    async def dashboard(self, ctx):
        """Group command for controlling the web dashboard for Red"""
        pass

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
        log = await self.conf.logerrors()
        if ctx.guild:
            secret = "[REDACTED]"
        else:
            secret = await self.conf.secret()
        redirect = await self.conf.redirect()
        support = await self.conf.support()
        description = (
            f"Error logging enabled: |  {log}\n"
            f"Client Secret:         |  {secret}\n"
            f"Redirect URI:          |  {redirect}\n"
            f"Support Server:        |  {support}"
        )
        embed.description = "```py\n" + description + "```"
        embed.set_footer(text="Dashboard created by Neuro Assassin")
        await ctx.send(embed=embed)
