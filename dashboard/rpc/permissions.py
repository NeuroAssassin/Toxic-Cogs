from typing import cast
from html import escape

import discord
from redbot.cogs.permissions.converters import CogOrCommand, GuildUniqueObjectFinder, RuleType
from redbot.core.bot import Red
from redbot.core.commands import commands
from redbot.core.utils import AsyncIter

from .utils import FakePermissionsContext, permcheck, rpccheck


class DashboardRPC_Permissions:
    def __init__(self, cog: commands.Cog):
        self.bot: Red = cog.bot
        self.cog: commands.Cog = cog

        # Initialize RPC handlers
        self.bot.register_rpc_handler(self.fetch_guild_rules)
        self.bot.register_rpc_handler(self.fetch_guild_targets)
        self.bot.register_rpc_handler(self.fetch_cog_commands)
        self.bot.register_rpc_handler(self.add_rule)
        self.bot.register_rpc_handler(self.add_default_rule)
        self.bot.register_rpc_handler(self.remove_rule)
        self.bot.register_rpc_handler(self.remove_default_rule)

    def unload(self):
        self.bot.unregister_rpc_handler(self.fetch_guild_rules)
        self.bot.unregister_rpc_handler(self.fetch_guild_targets)
        self.bot.unregister_rpc_handler(self.fetch_cog_commands)
        self.bot.unregister_rpc_handler(self.add_rule)
        self.bot.unregister_rpc_handler(self.add_default_rule)
        self.bot.unregister_rpc_handler(self.remove_rule)
        self.bot.unregister_rpc_handler(self.remove_default_rule)

    @rpccheck()
    @permcheck("Permissions", ["permissions"])
    async def fetch_guild_rules(self, guild: discord.Guild, member: discord.Member):
        permcog = self.bot.get_cog("Permissions")

        # Basically a copy and paste of perms._yaml_get_guild, except doesn't save to a yaml file
        # and instead returns JSON data, and tinkers with the data
        guild_rules = {}
        for category in ("COG", "COMMAND"):
            guild_rules.setdefault(category, {})
            rules_dict = await permcog.config.custom(category).all()
            for cmd_name, cmd_rules in rules_dict.items():
                model_rules = cmd_rules.get(str(guild.id))
                if model_rules is not None:
                    for target, rule in model_rules.items():
                        if cmd_name not in guild_rules[category]:
                            guild_rules[category][cmd_name] = []

                        if target != "default":
                            if rule is None:
                                continue
                            target = int(target)
                            obj = None
                            name = ""
                            objtype = ""
                            if obj := guild.get_channel(target):
                                objtype = "Channel"
                                name = obj.name
                            elif obj := guild.get_role(target):
                                objtype = "Role"
                                name = obj.name
                            elif obj := guild.get_member(target):
                                objtype = "User"
                                name = f"{obj.display_name}#{obj.discriminator}"
                            else:
                                continue

                            saving = {
                                "type": objtype,
                                "name": escape(name),
                                "id": str(target),
                                "permission": "allowed" if rule else "denied",
                            }
                        else:
                            if rule is None:
                                continue
                            saving = {
                                "type": "Default",
                                "permission": "allowed" if rule else "denied",
                            }

                        guild_rules[category][cmd_name].append(saving)
                    if not guild_rules[category].get(cmd_name, True):
                        del guild_rules[category][cmd_name]

        return guild_rules

    @rpccheck()
    @permcheck("Permissions", ["permissions"])
    async def fetch_guild_targets(self, guild: discord.Guild, member: discord.Member):
        data = {"USERS": [], "ROLES": [], "CHANNELS": []}

        async for user in AsyncIter(guild.members, steps=1300):
            data["USERS"].append(
                (str(user.id), escape(f"{user.display_name}#{user.discriminator}"))
            )

        async for role in AsyncIter(guild.roles, steps=1300):
            data["ROLES"].append((str(role.id), escape(role.name)))

        async for channel in AsyncIter(guild.channels, steps=1300):
            data["CHANNELS"].append((str(channel.id), escape(channel.name)))

        return data

    @rpccheck()
    @permcheck("Permissions", ["permissions"])
    async def fetch_cog_commands(self, guild: discord.Guild, member: discord.Member):
        data = {
            "COGS": list(self.bot.cogs.keys()),
            "COMMANDS": await self.cog.rpc.build_cmd_list(self.bot.commands, details=False),
        }

        return data

    @rpccheck()
    @permcheck("Permissions", ["permissions"])
    async def add_rule(
        self, guild: discord.Guild, member: discord.Member, t: str, target: int, command: str
    ):
        ctx = FakePermissionsContext(self.bot, guild)
        cog = self.bot.get_cog("Permissions")
        try:
            cog_or_command = await CogOrCommand.convert(ctx, command)
        except commands.BadArgument:
            return {"status": 0, "message": "Invalid command"}

        try:
            allow_or_deny = RuleType(t)
        except commands.BadArgument:
            return {"status": 0, "message": "Invalid action"}

        try:
            who_or_what = await GuildUniqueObjectFinder.convert("", ctx, str(target))
        except commands.BadArgument:
            return {"status": 0, "message": "Invalid target"}

        if isinstance(cog_or_command.obj, commands._AlwaysAvailableCommand):
            return {"status": 0, "message": "That command can not be restricted"}

        await cog._add_rule(
            rule=cast(bool, allow_or_deny),
            cog_or_cmd=cog_or_command,
            model_id=who_or_what.id,
            guild_id=guild.id,
        )

        return {"status": 1}

    @rpccheck()
    @permcheck("Permissions", ["permissions"])
    async def add_default_rule(
        self, guild: discord.Guild, member: discord.Member, t: str, command: str
    ):
        ctx = FakePermissionsContext(self.bot, guild)
        cog = self.bot.get_cog("Permissions")
        try:
            cog_or_command = await CogOrCommand.convert(ctx, command)
        except commands.BadArgument:
            return {"status": 0, "message": "Invalid command"}

        try:
            allow_or_deny = RuleType(t)
        except commands.BadArgument:
            return {"status": 0, "message": "Invalid action"}

        if isinstance(cog_or_command.obj, commands._AlwaysAvailableCommand):
            return {"status": 0, "message": "That command can not be restricted"}

        await cog._set_default_rule(
            rule=cast(bool, allow_or_deny), cog_or_cmd=cog_or_command, guild_id=guild.id,
        )

        return {"status": 1}

    @rpccheck()
    @permcheck("Permissions", ["permissions"])
    async def remove_rule(
        self, guild: discord.Guild, member: discord.Member, target: int, command: str
    ):
        ctx = FakePermissionsContext(self.bot, guild)
        cog = self.bot.get_cog("Permissions")
        try:
            cog_or_command = await CogOrCommand.convert(ctx, command)
        except commands.BadArgument:
            return {"status": 0, "message": "Invalid command"}

        try:
            who_or_what = await GuildUniqueObjectFinder.convert("", ctx, str(target))
        except commands.BadArgument:
            return {"status": 0, "message": "Invalid target"}

        await cog._remove_rule(
            cog_or_cmd=cog_or_command, model_id=who_or_what.id, guild_id=guild.id,
        )

        return {"status": 1}

    @rpccheck()
    @permcheck("Permissions", ["permissions"])
    async def remove_default_rule(
        self, guild: discord.Guild, member: discord.Member, command: str
    ):
        ctx = FakePermissionsContext(self.bot, guild)
        cog = self.bot.get_cog("Permissions")
        try:
            cog_or_command = await CogOrCommand.convert(ctx, command)
        except commands.BadArgument:
            return {"status": 0, "message": "Invalid command"}

        if isinstance(cog_or_command.obj, commands._AlwaysAvailableCommand):
            return {"status": 0, "message": "That command can not be restricted"}

        await cog._set_default_rule(
            rule=None, cog_or_cmd=cog_or_command, guild_id=guild.id,
        )

        return {"status": 1}
