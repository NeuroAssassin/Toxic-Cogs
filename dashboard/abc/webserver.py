from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box, humanize_list, inline
from redbot.core.utils.predicates import MessagePredicate
import discord

from dashboard.abc.abc import MixinMeta
from dashboard.abc.mixin import dashboard

from dashboard.baserpc import HUMANIZED_PERMISSIONS
from dashboard.menus import ClientList, ClientMenu


class DashboardWebserverMixin(MixinMeta):
    @checks.is_owner()
    @dashboard.group()
    async def webserver(self, ctx):
        """Group command for controlling settings related to webserver"""
        pass

    @webserver.command(enabled=False)
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

    @webserver.group()
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

    @webserver.command()
    async def secret(self, ctx: commands.Context, *, secret: str):
        """Set the client secret needed for Discord Oauth."""
        await self.config.secret.set(secret)
        await ctx.tick()

    @webserver.command()
    async def redirect(self, ctx: commands.Context, redirect: str):
        """Set the redirect for after logging in via Discord OAuth."""
        if not redirect.endswith("/callback"):
            await ctx.send("Redirect must end with `/callback`")
            return
        await self.config.redirect.set(redirect)
        await ctx.tick()

    @webserver.command(hidden=True)
    async def clientid(self, ctx: commands.Context, cid: int):
        """Set the Client ID for after logging in via Discord OAuth.
        
        Note that this should almost never be used.  This is only here
        for special cases where the Client ID is not the same as the bot
        ID.
        
        Pass 0 if you wish to revert to Bot ID."""
        await ctx.send(
            "**Warning**\n\nThis command only exists for special cases.  It is most likely that your client ID is your bot ID, which is the default.  **Changing this will break Discord OAuth until reverted.** Are you sure you want to do this?"
        )

        pred = MessagePredicate.yes_or_no(ctx)
        await self.bot.wait_for("message", check=pred)

        if pred.result is True:
            await self.config.clientid.set(cid)
            if cid == 0:
                await ctx.send("Client ID restored to bot ID.")
            else:
                await ctx.send(f"Client ID set to {cid}.")
        else:
            await ctx.send("Cancelled.")
