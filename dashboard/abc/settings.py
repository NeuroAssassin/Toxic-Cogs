from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box, humanize_list, inline
from redbot import __version__ as red_version
from typing import Optional
import discord
import platform
import socket
import pip
import sys
import os

from dashboard.abc.abc import MixinMeta
from dashboard.abc.mixin import dashboard

from dashboard.baserpc import HUMANIZED_PERMISSIONS
from dashboard.menus import ClientList, ClientMenu

THEME_COLORS = ["red", "primary", "blue", "green", "greener", "yellow"]


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
            in_use = s.connect_ex(('localhost', 42356)) == 0
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
                f"The following permissions are disabled for assigning: {humanize_list(disallowed)}"
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
                    f"**Permissions enabled**: {humanize_list(list(map(inline, changed or ['None'])))}\n"
                    f"**Permissions already enabled**: {humanize_list(list(map(inline, not_changed or ['None'])))}\n"
                    f"**Permissions unidentified**: {humanize_list(list(map(inline, missing or ['None'])))}\n"
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
                    f"**Permissions disabled**: {humanize_list(list(map(inline, changed or ['None'])))}\n"
                    f"**Permissions already disabled**: {humanize_list(list(map(inline, not_changed or ['None'])))}\n"
                    f"**Permissions unidentified**: {humanize_list(list(map(inline, missing or ['None'])))}\n"
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
        color = color.lower()
        if color == "purple":
            color = "primary"
        if color not in THEME_COLORS:
            return await ctx.send(
                f"Unrecognized color.  Please choose one of the following:\n{humanize_list(tuple(map(lambda x: inline(x).title(), THEME_COLORS)))}"
            )
        await self.config.defaultcolor.set(color)
        await ctx.tick()

    @settings.command()
    async def support(self, ctx: commands.Context, url: str = ""):
        """Set the URL for support.  This is recommended to be a Discord Invite.

        Leaving it blank will remove it.
        """
        await self.config.support.set(url)
        await ctx.tick()

    @settings.group()
    async def meta(self, ctx: commands.Context):
        """Control meta tags that are rendered by a service.

        For example, Discord rendering a link with an embed"""
        pass

    @meta.command()
    async def title(self, ctx, *, title: str = ""):
        """Set the meta title tag for the rendered UI from link.

        For Discord, this is the larger text hyperlinked to the url.
        
        The following arguments will be replaced if they are in the title:
            {name} | The bot's username"""
        await self.config.meta.title.set(title)
        if not title:
            return await ctx.send("Meta title reset to default.")
        await ctx.tick()

    @meta.command()
    async def icon(self, ctx, link: Optional[str] = ""):
        """Set the meta icon tag for the rendered UI from link.

        For Discord, this is the large icon in the top right of the embed."""
        await self.config.meta.icon.set(link)
        if not link:
            return await ctx.send("Meta icon reset to default.")
        await ctx.tick()

    @meta.command()
    async def description(self, ctx, *, description: str = ""):
        """Set the meta description tag for the rendered UI from link.

        For Discord, this is the smaller text under the title.
        
        The following arguments will be replaced if they are in the title:
            {name} | The bot's username"""
        await self.config.meta.description.set(description)
        if not description:
            return await ctx.send("Meta description reset to default.")
        await ctx.tick()

    @meta.command(name="color")
    async def color_meta(self, ctx, *, color: discord.Colour = ""):
        """Set the meta color tag for the rendered UI from link.

        For Discord, this is the colored bar that appears in the left of the embed."""
        await self.config.meta.color.set(str(color))
        if not color:
            return await ctx.send("Meta color reset to default.")
        await ctx.tick()

    @settings.command()
    async def view(self, ctx: commands.Context):
        """View the current dashboard settings."""
        data = await self.config.all()
        redirect = data["redirect"]
        secret = data["secret"]
        support = data["support"]
        color = data["defaultcolor"]
        if not support:
            support = "[Not set]"
        description = (
            f"Client Secret:   |  {secret}\n"
            f"Redirect URI:    |  {redirect}\n"
            f"Support Server:  |  {support}\n"
            f"Default theme:   |  {color}"
        )
        embed = discord.Embed(title="Red V3 Dashboard Settings", color=0x0000FF)
        embed.description = box(description, lang="ini")
        embed.add_field(name="Dashboard Version", value=box(f"[{self.__version__}]", lang="ini"))
        embed.set_footer(text="Dashboard created by Neuro Assassin.")
        await ctx.author.send(embed=embed)
