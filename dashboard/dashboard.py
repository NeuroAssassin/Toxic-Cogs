from collections import defaultdict

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, humanize_list, inline

from .baserpc import HUMANIZED_PERMISSIONS, DashboardRPC
from .menus import ClientList, ClientMenu

THEME_COLORS = ["red", "primary", "blue", "green", "greener", "yellow"]


class Dashboard(commands.Cog):

    __version__ = "0.1.5a.dev1"

    def __init__(self, bot: Red):
        self.bot = bot

        self.config = Config.get_conf(self, identifier=473541068378341376)
        self.config.register_global(
            secret="[Not set]",
            redirect="http://127.0.0.1:42356",
            blacklisted=[],
            owner_perm=15,
            widgets=[],
            testwidgets=[],
            support="",
            defaultcolor="red",
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
        """Group command for controlling the web dashboard for Red."""

    @checks.guildowner()
    @dashboard.group()
    async def roles(self, ctx: commands.Context):
        """Customize the roles that have permission to certain parts of the dashboard."""

    @roles.command()
    async def create(self, ctx: commands.Context, role: discord.Role, *permissions):
        """Register a new discord role to access certain parts of the dashboard."""
        roles = await self.config.guild(ctx.guild).roles()
        if role.id in [r["roleid"] for r in roles]:
            await ctx.send(
                f"That role is already registered. Please edit with `{ctx.prefix}dashboard roles edit`."
            )
            return
        assigning = []
        missing = []
        for p in permissions:
            if p.lower() in HUMANIZED_PERMISSIONS:
                assigning.append(p.lower())
            else:
                missing.append(p)
        if assigning:
            async with self.config.guild(ctx.guild).roles() as data:
                data.append({"roleid": role.id, "perms": assigning})
            self.configcache[ctx.guild.id]["roles"].append({"roleid": role.id, "perms": assigning})
        else:
            await ctx.send("Failed to identify any permissions in list. Please try again.")
            return
        if await ctx.embed_requested():
            e = discord.Embed(
                title="Role Registered",
                description=(
                    f"**Permissions assigned**: {humanize_list(list(map(inline, assigning)))}\n"
                    f"**Permissions unidentified**: {humanize_list(list(map(inline, missing or ['None'])))}"
                ),
                color=(await ctx.embed_color()),
            )
            await ctx.send(embed=e)
        else:
            await ctx.send(
                f"**Role registered**```css\n"
                f"[Permissions assigned]: {humanize_list(assigning)}\n"
                f"[Permissions unidentified]: {humanize_list(missing or ['None'])}"
                "```"
            )

    @roles.command()
    async def edit(self, ctx: commands.Context, role: discord.Role, *permissions):
        """Edit the permissions registered with a registered role."""
        changing = []
        missing = []
        for p in permissions:
            if p.lower() in HUMANIZED_PERMISSIONS:
                changing.append(p.lower())
            else:
                missing.append(p.lower())

        if not changing:
            await ctx.send("Failed to identify any permissions in list. Please try again.")
            return

        roles = await self.config.guild(ctx.guild).roles()
        try:
            ro = [ro for ro in roles if ro["roleid"] == role.id][0]
        except IndexError:
            return await ctx.send("That role is not registered.")

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

        if await ctx.embed_requested():
            e = discord.Embed(
                title="Successfully edited role",
                description=(
                    f"**Permissions added**: {humanize_list(list(map(inline, added or ['None'])))}\n"
                    f"**Permissions removed**: {humanize_list(list(map(inline, removed or ['None'])))}\n"
                    f"**Permissions unidentified**: {humanize_list(list(map(inline, missing or ['None'])))}\n"
                ),
                color=(await ctx.embed_color()),
            )
            await ctx.send(embed=e)
        else:
            await ctx.send(
                "**Successfully edited role**```css\n"
                f"[Permissions added]: {humanize_list(added or ['None'])}\n"
                f"[Permissions removed]: {humanize_list(removed or ['None'])}\n"
                f"[Permissions unidentified]: {humanize_list(missing or ['None'])}"
                "```"
            )

    @roles.command()
    async def delete(self, ctx: commands.Context, *, role: discord.Role):
        """Unregister a role from the dashboard."""
        roles = await self.config.guild(ctx.guild).roles()
        try:
            ro = [ro for ro in roles if ro["roleid"] == role.id][0]
        except IndexError:
            return await ctx.send("That role is not registered.")

        del roles[roles.index(ro)]
        await self.config.guild(ctx.guild).roles.set(roles)
        self.configcache[ctx.guild.id]["roles"] = roles

        await ctx.send("Successfully deleted role.")

    @roles.command(name="list")
    async def roles_list(self, ctx: commands.Context):
        """List roles registered with dashboard."""
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
        """List permissions for a registered role."""
        roles = await self.config.guild(ctx.guild).roles()
        try:
            r = [ro for ro in roles if ro["roleid"] == role.id][0]
        except IndexError:
            return await ctx.send("That role is not registered.")

        description = ""

        if await ctx.embed_requested():
            for perm in r["perms"]:
                description += f"{inline(perm.title())}: {HUMANIZED_PERMISSIONS[perm]}\n"
            e = discord.Embed(description=f"**Role {role.mention} permissions**\n", color=0x0000FF)
            e.description += description
            await ctx.send(embed=e)
        else:
            for perm in r["perms"]:
                description += f"[{perm.title()}]: {HUMANIZED_PERMISSIONS[perm]}\n"
            await ctx.send(f"**Role {role.name} permissions**```css\n{description}```")

    @roles.command()
    async def perms(self, ctx: commands.Context):
        """Displays permission keywords matched with humanized descriptions."""
        if await ctx.embed_requested():
            e = discord.Embed(
                title="Dashboard permissions", description="", color=(await ctx.embed_color()),
            )
            for key, value in HUMANIZED_PERMISSIONS.items():
                e.description += f"{inline(key.title())}: {value}\n"
            await ctx.send(embed=e)
        else:
            description = ""
            for key, value in HUMANIZED_PERMISSIONS.items():
                description += f"[{key.title()}]: {value}\n"
            await ctx.send(f"**Dashboard permissions**```css\n{description}```")

    @checks.is_owner()
    @dashboard.group()
    async def settings(self, ctx: commands.Context):
        """Group command for setting up the web dashboard for this Red bot."""

    @settings.command(disabled=True)
    async def clients(self, ctx: commands.Context):
        """View connected RPC clients.  These could be dashboard or other processes.

        Only terminate them if they are looking suspicious."""
        return await ctx.send("This command is disabled.")
        clients = self.bot.rpc._rpc.clients
        if clients:
            await ClientMenu(
                source=ClientList(clients), clear_reactions_after=True, timeout=180
            ).start(ctx, wait=False)
        else:
            e = discord.Embed(title="No RPC Clients connected", color=await ctx.embed_color())
            await ctx.send(embed=e)

    @settings.command()
    async def color(self, ctx, color):
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
    async def blacklist(self, ctx: commands.Context):
        """Manage dashboard blacklist"""
        pass

    @blacklist.command(name="view")
    async def blacklist_view(self, ctx: commands.Context):
        """See blacklisted IP addresses"""
        blacklisted = await self.config.blacklisted() or ["None"]
        await ctx.author.send(
            f"The following IP addresses are blocked: {humanize_list(blacklisted)}"
        )

    @blacklist.command(name="remove")
    async def blacklist_remove(self, ctx: commands.Context, *, ip):
        """Remove an IP address from blacklist"""
        try:
            async with self.config.blacklisted() as data:
                data.remove(ip)
            await ctx.tick()
        except ValueError:
            await ctx.send("Couldn't find that IP in blacklist.")

    @blacklist.command(name="add")
    async def blacklist_add(self, ctx: commands.Context, *, ip):
        """Add an IP address to blacklist"""
        async with self.config.blacklisted() as data:
            data.append(ip)
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
        if not redirect.endswith("/callback"):
            await ctx.send("Redirect must end with `/callback`")
            return
        await self.config.redirect.set(redirect)
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
