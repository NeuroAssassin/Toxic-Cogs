from redbot.core.utils.predicates import MessagePredicate
from redbot.core import commands, Config, checks
from typing import Optional
import discord
import asyncio
import aiohttp

URL = "https://developers.auth.gg/HWID/"


class AuthGG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(
            "authgg", identifier=473541068378341376, force_registration=True
        )

        self.conf.register_global(roles=[])

    @commands.group()
    async def authgg(self, ctx):
        """Control your users from auth.gg straight from Discord"""

    @authgg.command()
    async def resethwid(self, ctx, *, name: Optional[str] = None):
        """Reset a user's HWID lock on auth.gg"""
        if not await self.bot.is_owner(ctx.author):
            roles = await self.conf.roles()
            has_role = False
            for r in ctx.author.roles:
                if r.id in roles:
                    has_role = True
            if not has_role:
                return

        key = (await self.bot.get_shared_api_tokens("authgg")).get("api_key")
        if key is None:
            return await ctx.send(
                f"The auth.gg key has not been set.  Please run `{ctx.prefix}set api authgg api_key,your_api_key_here` before running this command"
            )

        if name is None:
            pred = MessagePredicate.same_context(ctx)
            await ctx.send("Please enter the username of the user you wish to unlock")
            try:
                message = await self.bot.wait_for("message", check=pred, timeout=30.0)
            except asyncio.TimeoutError:
                return await ctx.send("Command timed out.")
            name = message.content

        async with aiohttp.ClientSession() as session:
            data = {"type": "reset", "authorization": key, "user": name}
            response = await session.get(URL, params=data)
            if response.status != 200:
                return await ctx.send(
                    f"Something went wrong while contacting the API.  Status code: {response.status}"
                )
            text = await response.json(content_type="text/html")
            if text["status"] == "success":
                return await ctx.send(f"Successfully reset {name}'s HWID")
            else:
                return await ctx.send(f"Failed to reset {name}'s HWID: {text['info']}")

    @checks.is_owner()
    @authgg.group()
    async def roles(self, ctx):
        """Control what roles have access to reseting a user's HWID"""

    @roles.command()
    async def add(self, ctx, *, role: discord.Role):
        """Add a role to the whitelist for resetting user's HWID"""
        roles = await self.conf.roles()
        if role.id in roles:
            return await ctx.send("That role is already registered")

        roles.append(role.id)
        await self.conf.roles.set(roles)
        await ctx.tick()

    @roles.command()
    async def remove(self, ctx, *, role: discord.Role):
        """Remove a role from the whitelist for resetting user's HWID"""
        roles = await self.conf.roles()
        if role.id not in roles:
            return await ctx.send("That role is not registered")

        roles.remove(role.id)
        await self.conf.roles.set(roles)
        await ctx.tick()

    @roles.command()
    async def clear(self, ctx):
        """Remove all currently whitelisted roles"""
        await self.conf.roles.set([])
        await ctx.tick()

    @roles.command(name="list")
    async def _list(self, ctx):
        """View all currently whitelisted roles"""
        roles = await self.conf.roles()
        if not roles:
            return await ctx.send("No roles are currently registered")
        message = "The following roles are currently registered:"
        for r in roles:
            role = ctx.guild.get_role(r)
            if role:
                message += f"\n{role.name}: {r}"
        await ctx.send(message)
