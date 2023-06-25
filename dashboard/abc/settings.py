from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box, humanize_list, inline
from redbot import __version__ as red_version
import discord
import platform
import socket
import pip
import sys
import os

from dashboard.abc.abc import MixinMeta
from dashboard.abc.mixin import DBMixin

from dashboard.baserpc import HUMANIZED_PERMISSIONS

dashboard = MixinMeta.dashboard

THEME_COLORS = ["red", "primary", "blue", "green", "greener", "yellow"]

dashboard = DBMixin.dashboard

class DashboardSettingsMixin(MixinMeta):
    @checks.is_owner()
    @dashboard.command()
    async def debug(self, ctx: commands.Context):
        """Fetches debug info about your installation."""
        message = await ctx.send(box("Fetching debug info...", lang="css"))

        if sys.platform == "linux":
            import distro

        IS_WINDOWS = os.name == "nt"
        IS_MAC = sys.platform == "darwin"
        IS_LINUX = sys.platform == "linux"

        pyver = "{}.{}.{} ({})".format(*sys.version_info[:3], platform.architecture()[0])
        pipver = pip.__version__
        redver = red_version
        dpyver = discord.__version__
        if IS_WINDOWS:
            os_info = platform.uname()
            osver = "{} {} (vrsion {})".format(os_info.system, os_info.release, os_info.version)
        elif IS_MAC:
            os_info = platform.mac_ver()
            osver = "Mac OSX {} {}".format(os_info[0], os_info[2])
        elif IS_LINUX:
            os_info = distro.linux_distribution()
            osver = "{} {}".format(os_info[0], os_info[1]).strip()
        else:
            osver = "Unknown operating system!"
        dbver = self.__version__
        ips = len(await self.config.secret()) == 32

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            in_use = s.connect_ex(("localhost", 42356)) == 0
        await message.edit(
            content=(
                "Dashboard cog installation:\n"
                + box(
                    "#Operating System\n"
                    f"[Operating System]       {osver}\n"
                    f"[Python Version]         {pyver}\n"
                    f"[Pip Version]            {pipver}\n"
                    f"[Red Version]            {redver}\n"
                    f"[D.py Version]           {dpyver}\n"
                    f"[Dashboard Version]      {dbver}\n"
                    "\n"
                    "#WS Configuration\n"
                    f"[Verified secret]        {ips}\n"
                    f"[RPC Enabled]            {self.bot.rpc_enabled}\n"
                    f"[RPC Port]               {self.bot.rpc_port}\n"
                    f"[Webserver Port Active]  {in_use}",
                    lang="css",
                )
            )
        )

    @checks.is_owner()
    @dashboard.group()
    async def settings(self, ctx: commands.Context):
        """Group command for setting up the web dashboard for this Red bot."""

    @settings.group()
    async def permissions(self, ctx: commands.Context):
        """Add/remove permissions from `[p]dashboard roles`"""
        return

    @permissions.command(name="disabled")
    async def permissions_disallowed(self, ctx: commands.Context):
        """See dissallowed permissions for `[p]dashboard roles`"""
        disallowed = await self.config.disallowedperms()
        if disallowed:
            await ctx.send(
                "The following permissions are disabled for assigning: "
                f"{humanize_list(disallowed)}"
            )
        else:
            await ctx.send("No permissions are disabled")

    @permissions.command(name="enable")
    async def permissions_enable(self, ctx: commands.Context, *permissions):
        """Re-enable permission(s) for `[p]dashboard roles`"""
        changing = set()
        missing = set()
        for p in permissions:
            if p.lower() in HUMANIZED_PERMISSIONS:
                changing.add(p.lower())
            else:
                missing.add(p.lower())

        data = await self.config.disallowedperms()
        previous = set(data)

        data = previous - changing
        changed = previous - data
        not_changed = changing - changed

        await self.config.disallowedperms.set(list(data))

        if await ctx.embed_requested():
            e = discord.Embed(
                title="Successfully edited permissions",
                description=(
                    "**Permissions enabled**: "
                    f"{humanize_list(list(map(inline, changed or ['None'])))}\n"
                    "**Permissions already enabled**: "
                    f"{humanize_list(list(map(inline, not_changed or ['None'])))}\n"
                    "**Permissions unidentified**: "
                    f"{humanize_list(list(map(inline, missing or ['None'])))}\n"
                ),
                color=(await ctx.embed_color()),
            )
            await ctx.send(embed=e)
        else:
            await ctx.send(
                "**Successfully edited role**```css\n"
                f"[Permissions enabled]: {humanize_list(changed or ['None'])}\n"
                f"[Permissions already enabled]: {humanize_list(not_changed or ['None'])}\n"
                f"[Permissions unidentified]: {humanize_list(missing or ['None'])}"
                "```"
            )

    @permissions.command(name="disable")
    async def permissions_disable(self, ctx: commands.Context, *permissions):
        """Disable permission(s) for `[p]dashboard roles`"""
        changing = set()
        missing = set()
        for p in permissions:
            if p.lower() in HUMANIZED_PERMISSIONS:
                changing.add(p.lower())
            else:
                missing.add(p.lower())

        data = await self.config.disallowedperms()
        previous = set(data)

        data = previous | changing
        changed = data - previous
        not_changed = changing - changed

        await self.config.disallowedperms.set(list(data))

        if await ctx.embed_requested():
            e = discord.Embed(
                title="Successfully edited permissions",
                description=(
                    "**Permissions disabled**: "
                    f"{humanize_list(list(map(inline, changed or ['None'])))}\n"
                    "**Permissions already disabled**: "
                    f"{humanize_list(list(map(inline, not_changed or ['None'])))}\n"
                    "**Permissions unidentified**: "
                    f"{humanize_list(list(map(inline, missing or ['None'])))}\n"
                ),
                color=(await ctx.embed_color()),
            )
            await ctx.send(embed=e)
        else:
            await ctx.send(
                "**Successfully edited role**```css\n"
                f"[Permissions disabled]: {humanize_list(changed or ['None'])}\n"
                f"[Permissions already disabled]: {humanize_list(not_changed or ['None'])}\n"
                f"[Permissions unidentified]: {humanize_list(missing or ['None'])}"
                "```"
            )

    @settings.command(name="color")
    async def color_settings(self, ctx, color: str):
        """Set the default color for a new user.

        The webserver version must be at least 0.1.3a.dev in order for this to work."""
        return await ctx.send(
            "This command has been migrated to the webserver in the admin panel."
        )

    @settings.command()
    async def support(self, ctx: commands.Context, url: str = ""):
        """Set the URL for support.  This is recommended to be a Discord Invite.

        Leaving it blank will remove it.
        """
        return await ctx.send(
            "This command has been migrated to the webserver in the admin panel."
        )

    @settings.command()
    async def meta(self, ctx: commands.Context):
        """Control meta tags that are rendered by a service.

        For example, Discord rendering a link with an embed"""
        return await ctx.send(
            "This command has been migrated to the webserver in the admin panel."
        )

    @settings.command()
    async def view(self, ctx: commands.Context):
        """View the current dashboard settings."""
        return await ctx.send(
            "This command has been migrated to the webserver in the admin panel."
        )
