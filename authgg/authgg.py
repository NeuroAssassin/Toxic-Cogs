from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.chat_formatting import humanize_list, inline
from redbot.core import commands, Config, checks
from typing import Optional
import discord
import asyncio
import aiohttp

HWID_URL = "https://developers.auth.gg/HWID/"
USERS_URL = "https://developers.auth.gg/USERS/"


class AuthGG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(
            "authgg", identifier=473541068378341376, force_registration=True
        )

        self.conf.register_global(roles=[], keys={})

    @commands.group()
    async def authgg(self, ctx):
        """Control your users from auth.gg straight from Discord"""

    @authgg.command()
    async def resethwid(self, ctx, apikey: str, *, name: Optional[str] = None):
        """Reset a user's HWID lock on auth.gg for the specified API key name.
        
        The API key name must be the friendly name provided by `[p]authgg keys add`."""
        if not await self.bot.is_owner(ctx.author):
            roles = await self.conf.roles()
            has_role = False
            for r in ctx.author.roles:
                if r.id in roles:
                    has_role = True
            if not has_role:
                return

        key = (await self.conf.keys()).get(apikey)
        if key is None:
            return await ctx.send(
                f"That API key is not registered.  Please run `{ctx.prefix}authgg keys add {apikey} your_api_key_here` before running this command"
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
            response = await session.get(HWID_URL, params=data)
            if response.status != 200:
                return await ctx.send(
                    f"Something went wrong while contacting the API.  Status code: {response.status}"
                )
            text = await response.json(content_type="text/html")
            if text["status"] == "success":
                return await ctx.send(f"Successfully reset {name}'s HWID")
            else:
                return await ctx.send(f"Failed to reset {name}'s HWID: {text['info']}")

    @authgg.command()
    async def changepw(self, ctx, apikey: str, username: str, password: str):
        """Set a user's password to the specified input for the specified API key name.

        The API key name must be the friendly name provided by `[p]authgg keys add`."""
        if not await self.bot.is_owner(ctx.author):
            roles = await self.conf.roles()
            has_role = False
            for r in ctx.author.roles:
                if r.id in roles:
                    has_role = True
            if not has_role:
                return

        key = (await self.conf.keys()).get(apikey)
        if key is None:
            return await ctx.send(
                f"That API key is not registered.  Please run `{ctx.prefix}authgg keys add {apikey} your_api_key_here` before running this command"
            )

        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "type": "changepw",
                    "authorization": key,
                    "user": username,
                    "password": password,
                }
                response = await session.get(USERS_URL, params=data)
                if response.status != 200:
                    return await ctx.send(
                        f"Something went wrong while contacting the API.  Status code: {response.status}"
                    )
                text = await response.json(content_type="text/html")
                if text["status"] == "success":
                    return await ctx.send(f"Successfully set {username}'s password")
                else:
                    return await ctx.send(f"Failed to reset {username}'s password: {text['info']}")
        finally:
            try:
                await ctx.message.delete()
            except:
                await ctx.send(
                    "I was unable to delete your command message due to lack of perms.  It is recommended to due so to prevent your user's password from getting leaked."
                )

    @checks.is_owner()
    @authgg.group()
    async def keys(self, ctx):
        """Manage API keys for auth.gg"""

    @keys.command(name="add")
    async def _keys_add(self, ctx, friendly: str, key: str):
        """Register an auth.gg API key under a friendly name"""
        keys = await self.conf.keys()
        try:
            if friendly in keys:
                return await ctx.send("That friendly name is already registered.")
            keys[friendly] = key
            await self.conf.keys.set(keys)
        finally:
            try:
                await ctx.message.delete()
            except:
                await ctx.send(
                    "I was unable to delete your command message due to lack of perms.  It is recommended to due so to prevent your API key from getting leaked."
                )
            await ctx.send(f"Successfully registered API key under `{friendly}`")

    @keys.command(name="remove")
    async def _keys_remove(self, ctx, friendly: str):
        """Remove an auth.gg API key via its friendly name"""
        keys = await self.conf.keys()
        if friendly not in keys:
            return await ctx.send("That friendly name is not registered.")
        del keys[friendly]
        await self.conf.keys.set(keys)
        await ctx.tick()

    @keys.command(name="clear")
    async def _keys_clear(self, ctx):
        """Clears all auth.gg API keys"""
        await self.conf.keys.set({})
        await ctx.tick()

    @keys.command(name="list")
    async def _keys_list(self, ctx):
        """Lists registered auth.gg API keys by their friendly name"""
        keys = await self.conf.keys()
        if not keys:
            return await ctx.send("No API keys are currently registered")
        message = f"The following keys are currently registered: {humanize_list(list(map(inline, keys.keys())))}"
        await ctx.send(message)

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
