"""
MIT License

Copyright (c) 2018-Present NeuroAssassin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from redbot.core.bot import Red
from redbot.core import commands, Config
from typing import Optional
import datetime
import contextlib
import discord
import random
import asyncio
import time

from abc import ABC

# ABC Mixins
from reacticket.extensions.mixin import RTMixin
from reacticket.extensions.base import ReacTicketBaseMixin
from reacticket.extensions.basesettings import ReacTicketBaseSettingsMixin
from reacticket.extensions.closesettings import ReacTicketCloseSettingsMixin
from reacticket.extensions.usersettings import ReacTicketUserSettingsMixin


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """This allows the metaclass used for proper type detection to coexist with discord.py's
    metaclass."""


class ReacTicket(
    ReacTicketBaseMixin,
    ReacTicketBaseSettingsMixin,
    ReacTicketCloseSettingsMixin,
    ReacTicketUserSettingsMixin,
    RTMixin,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    def __init__(self, bot: Red):
        self.bot: Red = bot

        default_guild = {
            # Initial ticket creation settings
            "reaction": "\N{ADMISSION TICKETS}",
            "msg": "0-0",
            "openmessage": "{default}",
            "maxtickets": 1,
            "maxticketsenddm": False,
            # Permission settings
            "usercanclose": False,
            "usercanmodify": False,
            "usercanname": False,
            # Post creation settings
            "category": 0,
            "archive": {"category": 0, "enabled": False},
            "dm": False,
            "presetname": {"chosen": 0, "presets": ["ticket-{userid}"]},
            "closeonleave": False,
            "closeafter": 0,
            "exemptlist": [],
            # Miscellaneous
            "supportroles": [],
            "blacklist": [],
            "report": 0,
            "enabled": False,
            "created": {},
        }

        self.config: Config = Config.get_conf(
            self, identifier=473541068378341376, force_registration=True
        )
        self.config.register_guild(**default_guild)
        self.config.register_global(
            first_migration=False,
            second_migration=False,
            third_migration=False,
            fourth_migration=False,
        )
        self.bot.loop.create_task(self.possibly_migrate())

    async def possibly_migrate(self):
        await self.bot.wait_until_red_ready()

        has_migrated: bool = await self.config.first_migration()
        if not has_migrated:
            await self.migrate_first()

        has_second_migrated: bool = await self.config.second_migration()
        if not has_second_migrated:
            await self.migrate_second()

        has_third_migrated: bool = await self.config.third_migration()
        if not has_third_migrated:
            await self.migrate_third()

        has_fourth_migrated: bool = await self.config.fourth_migration()
        if not has_fourth_migrated:
            await self.migrate_fourth()

    async def migrate_first(self):
        guilds = self.config._get_base_group(self.config.GUILD)
        async with guilds.all() as data:
            for guild_id, guild_data in data.items():
                saving = {}
                try:
                    for user_id, ticket in guild_data["created"].items():
                        saving[user_id] = {"channel": ticket, "added": []}
                except KeyError:
                    continue

                data[guild_id]["created"] = saving
        await self.config.first_migration.set(True)

    async def migrate_second(self):
        guilds = self.config._get_base_group(self.config.GUILD)
        async with guilds.all() as data:
            for guild_id, guild_data in data.items():
                saving = {}
                try:
                    for user_id, ticket in guild_data["created"].items():
                        saving[user_id] = [ticket]
                except KeyError:
                    continue

                data[guild_id]["created"] = saving

        await self.config.second_migration.set(True)

    async def migrate_third(self):
        guilds = self.config._get_base_group(self.config.GUILD)
        async with guilds.all() as data:
            for guild_id, guild_data in data.items():
                saving = {}
                try:
                    for user_id, tickets in guild_data["created"].items():
                        saving[user_id] = tickets
                        for index, ticket in enumerate(tickets):
                            ticket["assigned"] = 0
                            saving[user_id][index] = ticket
                except KeyError:
                    continue

                data[guild_id]["created"] = saving

        await self.config.third_migration.set(True)

    async def migrate_fourth(self):
        guilds = self.config._get_base_group(self.config.GUILD)
        async with guilds.all() as data:
            for guild_id, guild_data in data.items():
                saving = {}
                try:
                    for user_id, tickets in guild_data["created"].items():
                        saving[user_id] = tickets
                        for index, ticket in enumerate(tickets):
                            ticket["locked"] = False
                            saving[user_id][index] = ticket
                except KeyError:
                    continue

                data[guild_id]["created"] = saving

        await self.config.fourth_migration.set(True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild_settings = await self.config.guild(member.guild).all()

        if not guild_settings["closeonleave"]:
            return

        if (
            not str(member.id) in guild_settings["created"]
            or len(guild_settings["created"][str(member.id)]) == 0
        ):
            return

        archive = self.bot.get_channel(guild_settings["archive"]["category"])
        post_processing = {}  # Mapping of Dict[discord.TextChannel: List[discord.Member]]

        for ticket in guild_settings["created"][str(member.id)]:
            channel: Optional[discord.TextChannel] = self.bot.get_channel(ticket["channel"])
            added_users = [user for u in ticket["added"] if (user := member.guild.get_member(u))]
            if guild_settings["report"] != 0:
                reporting_channel: Optional[discord.TextChannel] = self.bot.get_channel(
                    guild_settings["report"]
                )
                if reporting_channel:
                    if await self.embed_requested(reporting_channel):
                        embed = discord.Embed(
                            title="Ticket Closed",
                            description=(
                                f"Ticket {channel.mention} created by "
                                f"{member.mention} "
                                f"has been closed due to the user leaving the guild."
                            ),
                            color=await self.bot.get_embed_color(reporting_channel),
                        )
                        if ticket["assigned"]:
                            moderator = getattr(
                                member.guild.get_member(
                                    ticket["assigned"], "mention", "Unknown moderator"
                                )
                            )
                            embed.add_field(name="Assigned moderator", value=moderator)
                        await reporting_channel.send(embed=embed)
                    else:
                        message = (
                            f"Ticket {channel.mention} created by "
                            f"{str(member)} "
                            f"has been closed due to the user leaving the guild."
                        )
                        if ticket["assigned"]:
                            moderator = getattr(
                                member.guild.get_member(
                                    ticket["assigned"], "mention", "Unknown moderator"
                                )
                            )
                            message += f"\nAssigned moderator: {moderator}"
                        await reporting_channel.send(
                            message, allowed_mentions=discord.AllowedMentions.none()
                        )
            if guild_settings["archive"]["enabled"] and channel and archive:
                for user in added_users:
                    with contextlib.suppress(discord.HTTPException):
                        if user:
                            await channel.set_permissions(
                                user, send_messages=False, read_messages=True
                            )
                await channel.send(
                    f"Ticket {channel.mention} for {member.display_name} has been closed "
                    "due to author leaving.  Channel will be moved to archive in one minute."
                )

                post_processing[channel] = added_users
            else:
                if channel:
                    for user in added_users:
                        with contextlib.suppress(discord.HTTPException):
                            if user:
                                await channel.set_permissions(
                                    user, send_messages=False, read_messages=True
                                )
                await channel.send(
                    f"Ticket {channel.mention} for {member.display_name} has been closed "
                    "due to author leaving.  Channel will be deleted in one minute, if exists."
                )
            async with self.config.guild(member.guild).created() as tickets:
                if str(member.id) in tickets:
                    del tickets[str(member.id)]

        await asyncio.sleep(60)

        for channel, added_users in post_processing.items():
            if guild_settings["archive"]["enabled"] and channel and archive:
                try:
                    admin_roles = [
                        member.guild.get_role(role_id)
                        for role_id in (await self.bot._config.guild(member.guild).admin_role())
                        if member.guild.get_role(role_id)
                    ]
                    support_roles = [
                        member.guild.get_role(role_id)
                        for role_id in guild_settings["supportroles"]
                        if member.guild.get_role(role_id)
                    ]

                    all_roles = admin_roles + support_roles
                    overwrites = {
                        member.guild.default_role: discord.PermissionOverwrite(
                            read_messages=False
                        ),
                        member.guild.me: discord.PermissionOverwrite(
                            read_messages=True,
                            send_messages=True,
                            manage_channels=True,
                            manage_permissions=True,
                        ),
                    }
                    for role in all_roles:
                        overwrites[role] = discord.PermissionOverwrite(
                            read_messages=True, send_messages=True
                        )
                    for user in added_users:
                        if user:
                            overwrites[user] = discord.PermissionOverwrite(read_messages=False)
                    await channel.edit(category=archive, overwrites=overwrites)
                except discord.HTTPException as e:
                    await channel.send(f"Failed to move to archive: {str(e)}")
            else:
                if channel:
                    try:
                        await channel.delete()
                    except discord.HTTPException:
                        with contextlib.suppress(discord.HTTPException):
                            await channel.send(
                                'Failed to delete channel. Please ensure I have "Manage Channels" '
                                "permission in the category."
                            )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if not payload.guild_id:
            return

        guild_settings = await self.config.guild_from_id(payload.guild_id).all()
        if not guild_settings["enabled"]:
            return

        if guild_settings["msg"] == "0-0":
            await self.config.guild_from_id(payload.guild_id).enabled.set(False)
            return

        if guild_settings["msg"] != f"{payload.channel_id}-{payload.message_id}":
            return

        if (guild_settings["reaction"].isdigit() and payload.emoji.is_unicode_emoji()) or (
            not guild_settings["reaction"].isdigit() and payload.emoji.is_custom_emoji()
        ):
            return

        if payload.emoji.is_custom_emoji():
            if payload.emoji.id != int(guild_settings["reaction"]):
                return
        else:
            if str(payload.emoji) != guild_settings["reaction"]:
                return

        category = self.bot.get_channel(guild_settings["category"])
        if not category:
            await self.config.guild_from_id(payload.guild_id).enabled.set(False)
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not category.permissions_for(guild.me).administrator:
            await self.config.guild_from_id(payload.guild_id).enabled.set(False)
            return

        if payload.user_id in guild_settings["blacklist"]:
            return

        user = guild.get_member(payload.user_id)

        if (
            len(guild_settings["created"].get(str(payload.user_id), []))
            >= guild_settings["maxtickets"]
        ):
            if guild_settings["maxticketsenddm"]:
                try:
                    await user.send(
                        f"You have reached the maximum number of tickets in {guild.name}."
                    )
                except discord.HTTPException:
                    pass

            with contextlib.suppress(discord.HTTPException):
                message = await self.bot.get_channel(payload.channel_id).fetch_message(
                    payload.message_id
                )
                await message.remove_reaction(payload.emoji, member=user)
            return

        admin_roles = [
            guild.get_role(role_id)
            for role_id in (await self.bot._config.guild(guild).admin_role())
            if guild.get_role(role_id)
        ]
        support_roles = [
            guild.get_role(role_id)
            for role_id in (await self.config.guild(guild).supportroles())
            if guild.get_role(role_id)
        ]

        all_roles = admin_roles + support_roles

        can_read = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        can_read_and_manage = discord.PermissionOverwrite(
            read_messages=True, send_messages=True, manage_channels=True, manage_permissions=True
        )  # Since Discord can't make up their mind about manage channels/manage permissions

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: can_read_and_manage,
            user: can_read,
        }
        for role in all_roles:
            overwrites[role] = can_read

        now = datetime.datetime.now(datetime.timezone.utc)

        channel_name = (
            guild_settings["presetname"]["presets"][guild_settings["presetname"]["chosen"]]
            .replace("{user}", user.display_name)
            .replace("{userid}", str(user.id))
            .replace("{minute}", str(now.minute))
            .replace("{hour}", str(now.hour))
            .replace("{day_name}", now.strftime("%A"))
            .replace("{day}", str(now.day))
            .replace("{month_name}", now.strftime("%B"))
            .replace("{month}", str(now.month))
            .replace("{year}", str(now.year))
            .replace("{random}", str(random.randint(1, 100000)))
        )[:100]

        created_channel = await category.create_text_channel(channel_name, overwrites=overwrites)
        if guild_settings["openmessage"] == "{default}":
            if guild_settings["usercanclose"]:
                sent = await created_channel.send(
                    f"Ticket created for {user.display_name}\nTo close this, "
                    f"Administrators or {user.display_name} may run `[p]reacticket close`."
                )
            else:
                sent = await created_channel.send(
                    f"Ticket created for {user.display_name}\n"
                    "Only Administrators may close this by running `[p]reacticket close`."
                )
        else:
            try:
                message = (
                    guild_settings["openmessage"]
                    .replace("{mention}", user.mention)
                    .replace("{username}", user.display_name)
                    .replace("{id}", str(user.id))
                )
                sent = await created_channel.send(
                    message, allowed_mentions=discord.AllowedMentions(users=True, roles=True)
                )
            except Exception as e:
                # Something went wrong, let's go to default for now
                print(e)
                if guild_settings["usercanclose"]:
                    sent = await created_channel.send(
                        f"Ticket created for {user.display_name}\nTo close this, "
                        f"Administrators or {user.display_name} may run `[p]reacticket close`."
                    )
                else:
                    sent = await created_channel.send(
                        f"Ticket created for {user.display_name}\n"
                        "Only Administrators may close this by running `[p]reacticket close`."
                    )

        # To prevent race conditions...
        async with self.config.guild(guild).created() as created:
            if str(payload.user_id) not in created:
                created[str(payload.user_id)] = []
            created[str(payload.user_id)].append(
                {
                    "channel": created_channel.id,
                    "added": [],
                    "opened": time.time(),
                    "assigned": 0,
                    "locked": False,
                }
            )

        # If removing the reaction fails... eh
        with contextlib.suppress(discord.HTTPException):
            message = await self.bot.get_channel(payload.channel_id).fetch_message(
                payload.message_id
            )
            await message.remove_reaction(payload.emoji, member=user)

        if guild_settings["report"] != 0:
            reporting_channel = self.bot.get_channel(guild_settings["report"])
            if reporting_channel:
                if await self.embed_requested(reporting_channel):
                    embed = discord.Embed(
                        title="Ticket Opened",
                        description=(
                            f"Ticket created by {user.mention} has been opened.\n"
                            f"Click [here]({sent.jump_url}) to jump to the start of the ticket."
                        ),
                    )
                    description = ""
                    if guild_settings["usercanclose"]:
                        description += "Users are **allowed** to close their own tickets.\n"
                    else:
                        description += "Users are **not** allowed to close their own tickets.\n"

                    if guild_settings["usercanmodify"]:
                        description += (
                            "Users are **allowed** to add/remove "
                            "other users to/from their tickets.\n"
                        )
                    else:
                        description += (
                            "Users are **not** allowed to add/remove "
                            "other users to/from their tickets.\n"
                        )
                    embed.add_field(name="User Permission", value=description)
                    await reporting_channel.send(embed=embed)
                else:
                    message = (
                        f"Ticket created by {str(user)} has been opened.\n"
                        f"Here's a link ({sent.jump_url}) to jump to it.\n"
                    )

                    if guild_settings["usercanclose"] and guild_settings["usercanmodify"]:
                        message += (
                            "Users are **allowed** to close "
                            "and add/remove users to/from their tickets."
                        )
                    elif guild_settings["usercanclose"]:
                        message += (
                            "Users are **allowed** to close their tickets, "
                            "but cannot add/remove users."
                        )
                    elif guild_settings["usercanmodify"]:
                        message += (
                            "Users are **allowed** to add/remove users to/from their tickets, "
                            "but are **not** allowed to close."
                        )
                    else:
                        message += "Users cannot close or add/remove users to/from their tickets."

                    await reporting_channel.send(message)
