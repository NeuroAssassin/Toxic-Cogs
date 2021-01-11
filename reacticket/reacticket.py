from redbot.core.utils.mod import is_admin_or_superior
from redbot.core.bot import Red
from redbot.core import commands, checks, Config
from typing import Union, Optional
import discord
import contextlib
import asyncio
import time
import copy


class ReacTicket(commands.Cog):
    def __init__(self, bot: Red):
        self.bot: Red = bot

        default_guild = {
            # Initial ticket creation settings
            "reaction": "\N{ADMISSION TICKETS}",
            "msg": "0-0",
            "openmessage": "{default}",
            # Permission settings
            "usercanclose": False,
            "usercanmodify": False,
            # Post creation settings
            "category": 0,
            "archive": {"category": 0, "enabled": False},
            # Miscellaneous
            "supportroles": [],
            "blacklist": [],
            "report": 0,
            "enabled": False,
            "created": {},
        }

        self.config = Config.get_conf(self, identifier=473541068378341376, force_registration=True)
        self.config.register_guild(**default_guild)
        self.config.register_global(first_migration=False)
        self.bot.loop.create_task(self.possibly_migrate())

    async def possibly_migrate(self):
        await self.bot.wait_until_red_ready()
        has_migrated = await self.config.first_migration()
        if not has_migrated:
            await self.migrate()

    async def migrate(self):
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

    async def embed_requested(self, channel):
        # Copy of ctx.embed_requested, but with the context taken out
        if not channel.permissions_for(channel.guild.me).embed_links:
            return False

        channel_setting = await self.bot._config.channel(channel).embeds()
        if channel_setting is not None:
            return channel_setting

        guild_setting = await self.bot._config.guild(channel.guild).embeds()
        if guild_setting is not None:
            return guild_setting

        return await self.bot._config.embeds()

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

        if str(payload.user_id) in guild_settings["created"]:
            # User already has a ticket
            return

        category = self.bot.get_channel(guild_settings["category"])
        if not category:
            await self.config.guild_from_id(payload.guild_id).enabled.set(False)
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not category.permissions_for(guild.me).manage_channels:
            await self.config.guild_from_id(payload.guild_id).enabled.set(False)
            return

        if payload.user_id in guild_settings["blacklist"]:
            return

        user = guild.get_member(payload.user_id)
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

        created_channel = await category.create_text_channel(
            f"ticket-{payload.user_id}", overwrites=overwrites
        )
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
                sent = await created_channel.send(message)
            except Exception as e:
                print(e)
                return

        # To prevent race conditions...
        async with self.config.guild(guild).created() as created:
            created[payload.user_id] = {
                "channel": created_channel.id,
                "added": [],
                "opened": time.time(),
            }

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
                            f"Ticket created by {user.mention} has been opened.  "
                            f"Click [here]({sent.jump_url}) to jump to the start of the ticket."
                        ),
                    )
                    description = ""
                    if guild_settings["usercanclose"]:
                        description += "Users are allowed to close their own tickets.\n"
                    else:
                        description += "Users are **not** allowed to close their own tickets.\n"

                    if guild_settings["usercanmodify"]:
                        description += (
                            "Users are allowed to add/remove other users to/from their tickets.\n"
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
                        f"Ticket created by {str(user)} has been opened.  "
                        f"Click [here]({sent.jump_url}) to jump to it.\n"
                    )

                    if guild_settings["usercanclose"] and guild_settings["usercanmodify"]:
                        message += (
                            "Users are allowed to close "
                            "and add/remove users to/from their tickets."
                        )
                    elif guild_settings["usercanclose"]:
                        message += (
                            "Users are allowed to close their tickets, "
                            "but cannot add/remove users."
                        )
                    elif guild_settings["usercanmodify"]:
                        message += (
                            "Users are allowed to add/remove users to/from their tickets, "
                            "but cannot close."
                        )
                    else:
                        message += "Users cannot close or add/remove users to/from their tickets."

                    await reporting_channel.send(message)

    @checks.bot_has_permissions(add_reactions=True)
    @commands.guild_only()
    @commands.group()
    async def reacticket(self, ctx):
        """Create a reaction ticket system in your server"""
        pass

    @reacticket.command()
    async def close(self, ctx, author: discord.Member = None):
        """Closes the ticket created by the user"""
        guild_settings = await self.config.guild(ctx.guild).all()
        is_admin = await is_admin_or_superior(self.bot, ctx.author) or any(
            [ur.id in guild_settings["supportroles"] for ur in ctx.author.roles]
        )
        must_be_admin = not guild_settings["usercanclose"]

        if not is_admin and must_be_admin:
            await ctx.send("Only Administrators can close tickets.")
            return
        elif not is_admin:
            author = ctx.author  # no u
        elif is_admin and not author:
            # Let's try to get the current channel and get the author
            # If not, we'll default to ctx.author
            inverted = {}
            for author_id, ticket in guild_settings["created"].items():
                inverted[ticket["channel"]] = author_id
            try:
                author = ctx.guild.get_member(int(inverted[ctx.channel.id]))
            except KeyError:
                author = ctx.author

        if str(author.id) not in guild_settings["created"]:
            await ctx.send("That user does not have an open ticket.")
            return

        channel = self.bot.get_channel(guild_settings["created"][str(author.id)]["channel"])
        archive = self.bot.get_channel(guild_settings["archive"]["category"])
        added_users = [
            user
            for u in guild_settings["created"][str(author.id)]["added"]
            if (user := ctx.guild.get_member(u))
        ]
        added_users.append(author)

        # Again, to prevent race conditions...
        async with self.config.guild(ctx.guild).created() as created:
            del created[str(author.id)]

        if guild_settings["report"] != 0:
            reporting_channel = self.bot.get_channel(guild_settings["report"])
            if reporting_channel:
                if await self.embed_requested(reporting_channel):
                    embed = discord.Embed(
                        title="Ticket Closed",
                        description=(
                            f"Ticket created by {author.mention} has been closed by "
                            f"{ctx.author.mention}."
                        ),
                    )
                    await reporting_channel.send(embed=embed)
                else:
                    message = (
                        f"Ticket created by {str(author)} has been closed by {str(ctx.author)}."
                    )

                    await reporting_channel.send(message)

        if guild_settings["archive"]["enabled"] and channel and archive:
            for user in added_users:
                with contextlib.suppress(discord.HTTPException):
                    await channel.set_permissions(user, send_messages=False, read_messages=True)
            await ctx.send(
                f"Ticket for {author.display_name} has been closed.  "
                "Channel will be moved to archive in one minute."
            )

            await asyncio.sleep(60)

            try:
                admin_roles = [
                    ctx.guild.get_role(role_id)
                    for role_id in (await self.bot._config.guild(ctx.guild).admin_role())
                    if ctx.guild.get_role(role_id)
                ]
                support_roles = [
                    ctx.guild.get_role(role_id)
                    for role_id in (await self.config.guild(ctx.guild).supportroles())
                    if ctx.guild.get_role(role_id)
                ]

                all_roles = admin_roles + support_roles
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                }
                for role in all_roles:
                    overwrites[role] = discord.PermissionOverwrite(
                        read_messages=True, send_messages=True
                    )
                for user in added_users:
                    overwrites[user] = discord.PermissionOverwrite(read_messages=False)
                await channel.edit(category=archive, overwrites=overwrites)
            except discord.HTTPException as e:
                await ctx.send(f"Failed to move to archive: {str(e)}")
        else:
            if channel:
                for user in added_users:
                    with contextlib.suppress(discord.HTTPException):
                        await channel.set_permissions(
                            user, send_messages=False, read_messages=True
                        )
            await ctx.send(
                f"Ticket for {author.display_name} has been closed.  "
                "Channel will be deleted in one minute, if exists."
            )

            await asyncio.sleep(60)

            if channel:
                try:
                    await channel.delete()
                except discord.HTTPException:
                    with contextlib.suppress(discord.HTTPException):
                        await ctx.send(
                            'Failed to delete channel.  Please ensure I have "Manage Channels" '
                            "permission in the category."
                        )

    @reacticket.command(name="add")
    async def ticket_add(self, ctx, user: discord.Member):
        """Add a user to the current ticket."""
        guild_settings = await self.config.guild(ctx.guild).all()
        is_admin = await is_admin_or_superior(self.bot, ctx.author) or any(
            [ur.id in guild_settings["supportroles"] for ur in ctx.author.roles]
        )
        must_be_admin = not guild_settings["usercanmodify"]

        if not is_admin and must_be_admin:
            await ctx.send("Only Administrators can add/remove other users to tickets.")
            return
        elif not is_admin:
            author = ctx.author
        elif is_admin:
            # Since the author isn't specified, and it's an admin, we need to guess on who
            # the author is
            inverted = {}
            for author_id, ticket in guild_settings["created"].items():
                inverted[ticket["channel"]] = author_id
            try:
                author = ctx.guild.get_member(int(inverted[ctx.channel.id]))
            except KeyError:
                author = ctx.author

        if str(author.id) not in guild_settings["created"]:
            if not is_admin:
                await ctx.send("You do not have an open ticket.")
            else:
                await ctx.send(
                    "Failed to determine ticket.  "
                    "Please run command in the corresponding ticket channel."
                )
            return

        if user.id in guild_settings["created"][str(author.id)]["added"]:
            await ctx.send("That user is already added.")
            return

        adding_is_admin = await is_admin_or_superior(self.bot, user) or any(
            [ur.id in guild_settings["supportroles"] for ur in user.roles]
        )

        if adding_is_admin:
            await ctx.send("You cannot add a user in support or admin team.")
            return

        channel = self.bot.get_channel(guild_settings["created"][str(author.id)]["channel"])
        if not channel:
            await ctx.send("The ticket channel has been deleted.")

        try:
            await channel.set_permissions(user, send_messages=True, read_messages=True)
        except discord.Forbidden:
            await ctx.send(
                "The Manage Permissions channel for me has been removed.  "
                "I am unable to modify this ticket."
            )
            return

        async with self.config.guild(ctx.guild).created() as created:
            created[str(author.id)]["added"].append(user.id)

        await ctx.send(f"{user.mention} has been added to the ticket.")

    @reacticket.command(name="remove")
    async def ticket_remove(self, ctx, user: discord.Member):
        """Remove a user from the current ticket."""
        guild_settings = await self.config.guild(ctx.guild).all()
        is_admin = await is_admin_or_superior(self.bot, ctx.author) or any(
            [ur.id in guild_settings["supportroles"] for ur in ctx.author.roles]
        )
        must_be_admin = not guild_settings["usercanmodify"]

        if not is_admin and must_be_admin:
            await ctx.send("Only Administrators can add/remove other users to tickets.")
            return
        elif not is_admin:
            author = ctx.author
        elif is_admin:
            # Since the author isn't specified, and it's an admin, we need to guess on who
            # the author is
            inverted = {}
            for author_id, ticket in guild_settings["created"].items():
                inverted[ticket["channel"]] = author_id
            try:
                author = ctx.guild.get_member(int(inverted[ctx.channel.id]))
            except KeyError:
                author = ctx.author

        if str(author.id) not in guild_settings["created"]:
            if not is_admin:
                await ctx.send("You do not have an open ticket.")
            else:
                await ctx.send(
                    "Failed to determine ticket.  "
                    "Please run command in the corresponding ticket channel."
                )
            return

        if user.id not in guild_settings["created"][str(author.id)]["added"]:
            await ctx.send("That user is not added.")
            return

        removing_is_admin = await is_admin_or_superior(self.bot, user) or any(
            [ur.id in guild_settings["supportroles"] for ur in user.roles]
        )

        if removing_is_admin:
            await ctx.send("You cannot remove a user in support or admin team.")
            return

        channel = self.bot.get_channel(guild_settings["created"][str(author.id)]["channel"])
        if not channel:
            await ctx.send("The ticket channel has been deleted.")

        try:
            await channel.set_permissions(user, send_messages=False, read_messages=False)
        except discord.Forbidden:
            await ctx.send(
                "The Manage Permissions channel for me has been removed.  "
                "I am unable to modify this ticket."
            )
            return

        async with self.config.guild(ctx.guild).created() as created:
            created[str(author.id)]["added"].remove(user.id)

        await ctx.send(f"{user.mention} has been removed from the ticket.")

    @checks.admin()
    @reacticket.group(invoke_without_command=True)
    async def settings(self, ctx):
        """Manage settings for ReacTicket"""
        await ctx.send_help()
        guild_settings = await self.config.guild(ctx.guild).all()
        channel_id, message_id = list(map(int, guild_settings["msg"].split("-")))

        ticket_channel = getattr(self.bot.get_channel(channel_id), "name", "Not set")
        ticket_category = getattr(
            self.bot.get_channel(guild_settings["category"]), "name", "Not set"
        )
        archive_category = getattr(
            self.bot.get_channel(guild_settings["archive"]["category"]), "name", "Not set"
        )
        report_channel = getattr(self.bot.get_channel(guild_settings["report"]), "name", "Not set")

        await ctx.send(
            "```ini\n"
            f"[Ticket Channel]:    {ticket_channel}\n"
            f"[Ticket MessageID]:  {message_id}\n"
            f"[Ticket Reaction]:   {guild_settings['reaction']}\n"
            f"[User-closable]:     {guild_settings['usercanclose']}\n"
            f"[User-modifiable]:   {guild_settings['usercanmodify']}\n"
            f"[Ticket Category]:   {ticket_category}\n"
            f"[Report Channel]:    {report_channel}\n"
            f"[Archive Category]:  {archive_category}\n"
            f"[Archive Enabled]:   {guild_settings['archive']['enabled']}\n"
            f"[System Enabled]:    {guild_settings['enabled']}\n"
            "```"
        )

    @settings.command()
    async def setmsg(self, ctx, message: discord.Message):
        """Set the message to listen for ticket reactions on"""
        if not message.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(
                'I require "Manage Messages" permissions in that channel to execute that command.'
            )
            return

        msg = f"{message.channel.id}-{message.id}"
        await self.config.guild(ctx.guild).msg.set(msg)
        await ctx.send("Ticket message successfully set.")

    @settings.command()
    async def reaction(self, ctx, emoji: Union[discord.Emoji, str]):
        """Set the reaction to listen for on the Ticket Creation message"""
        if isinstance(emoji, discord.Emoji):
            if emoji.guild_id != ctx.guild.id:
                await ctx.send(
                    "Custom emojis must be from the same guild the ticket reaction system"
                    "is being set up in."
                )
                return
            test_emoji = emoji
            emoji = str(emoji.id)
        else:
            emoji = str(emoji).replace("\N{VARIATION SELECTOR-16}", "")
            test_emoji = emoji

        test_message = None
        channel_id, message_id = list(
            map(int, (await self.config.guild(ctx.guild).msg()).split("-"))
        )

        if channel_id == message_id == 0:
            test_message = ctx.message
        else:
            try:
                test_message = await self.bot.get_channel(channel_id).fetch_message(message_id)
            except (AttributeError, discord.NotFound, discord.Forbidden):
                # Channel/message no longer exists or we cannot access it
                await self.config.guild(ctx.guild).msg.set("0-0")
                test_message = ctx.message

        try:
            await test_message.add_reaction(test_emoji)
        except discord.HTTPException:
            await ctx.send("Invalid emoji.")
            return
        else:
            await test_message.remove_reaction(test_emoji, member=ctx.guild.me)

        await self.config.guild(ctx.guild).reaction.set(emoji)
        await ctx.send(f"Ticket reaction successfully set to {test_emoji}")

    @settings.command(name="creationmessage", aliases=["openmessage"])
    async def ticket_creation_message(self, ctx, *, message):
        """Set the message that is sent when you initially create the ticket.

        If any of these are included in the message, they will automatically be
        replaced with the corresponding value.
            {mention} - Mentions the user who created the ticket
            {username} - Username of the user who created the ticket
            {id} - ID of the user who created the ticket.

        To return to default, set the message to exactly "{default}" """
        await self.config.guild(ctx.guild).openmessage.set(message)
        if message == "{default}":
            await ctx.send("Ticket creation message restored to default.")
        else:
            await ctx.send("Ticket creation message successfully set.")

    @settings.command()
    async def usercanclose(self, ctx, yes_or_no: Optional[bool] = None):
        """Set whether users can close their own tickets or not."""
        if yes_or_no is None:
            yes_or_no = not await self.config.guild(ctx.guild).usercanclose()

        await self.config.guild(ctx.guild).usercanclose.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Users can now close their own tickets.")
        else:
            await ctx.send("Only administrators can now close tickets.")

    @settings.command()
    async def usercanmodify(self, ctx, yes_or_no: Optional[bool] = None):
        """Set whether users can add or remove additional users to their ticket."""
        if yes_or_no is None:
            yes_or_no = not await self.config.guild(ctx.guild).usercanmodify()

        await self.config.guild(ctx.guild).usercanmodify.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Users can now add/remove other users to their own tickets.")
        else:
            await ctx.send("Only administrators can now add/remove users to tickets.")

    @settings.command()
    async def blacklist(self, ctx, *, user: discord.Member = None):
        """Add or remove a user to be prevented from creating tickets.

        Useful for users who are creating tickets for no reason."""
        if user:
            async with self.config.guild(ctx.guild).blacklist() as blacklist:
                if user.id in blacklist:
                    blacklist.remove(user.id)
                    await ctx.send(
                        f"{user.display_name} has been removed from the reacticket blacklist."
                    )
                else:
                    blacklist.append(user.id)
                    await ctx.send(
                        f"{user.display_name} has been add to the reacticket blacklist."
                    )
        else:
            blacklist = await self.config.guild(ctx.guild).blacklist()
            if not blacklist:
                await ctx.send("No users have been blacklisted so far.")
                return
            e = discord.Embed(
                title="The following users are blacklisted from creating tickets.",
                description="",
                color=await ctx.embed_color(),
            )
            for u in blacklist:
                e.description += f"<@{u}> "
            await ctx.send(embed=e)

    @settings.command()
    async def roles(self, ctx, *, role: discord.Role = None):
        """Add or remove a role to be automatically added to Ticket channels.

        These will be seen as support roles, and will have access to archived ticket channels."""
        if role:
            async with self.config.guild(ctx.guild).supportroles() as roles:
                if role.id in roles:
                    roles.remove(role.id)
                    await ctx.send(
                        f"The {role.name} role will no longer be automatically added to tickets."
                    )
                else:
                    roles.append(role.id)
                    await ctx.send(
                        f"The {role.name} role will now automatically be added to tickets."
                    )
        else:
            roles = await self.config.guild(ctx.guild).supportroles()
            new = copy.deepcopy(roles)
            if not roles:
                await ctx.send("No roles are set to be added to tickets right now.")
                return
            e = discord.Embed(
                title="The following roles are automatically added to tickets.",
                description="Note that administrator roles will always be added by default.\n",
                color=await ctx.embed_color(),
            )
            for r in roles:
                ro = ctx.guild.get_role(r)
                if ro:
                    e.description += ro.mention + "\n"
                else:
                    new.remove(r)

            if new != roles:
                await self.config.guild(ctx.guild).supportroles.set(new)
            await ctx.send(embed=e)

    @settings.command()
    async def category(self, ctx, category: discord.CategoryChannel):
        """Set the category to create ticket channels under."""
        if not category.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(
                'I require "Manage Channels" permissions in that category to execute that command.'
            )
            return

        await self.config.guild(ctx.guild).category.set(category.id)
        await ctx.send(f"Ticket channels will now be created in the {category.name} category")

    @settings.group()
    async def archive(self, ctx):
        """Customize settings for archiving ticket channels"""
        pass

    @archive.command(name="category")
    async def archive_category(self, ctx, category: discord.CategoryChannel):
        """Set the category to move closed ticket channels to."""
        if not category.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(
                'I require "Manage Channels" permissions in that category to execute that command.'
            )
            return

        async with self.config.guild(ctx.guild).archive() as data:
            data["category"] = category.id
        await ctx.send(
            f"Closed ticket channels will now be moved to the {category.name} category, "
            "if Archive mode is enabled."
        )

    @archive.command(name="enable")
    async def archive_enable(self, ctx, yes_or_no: bool = None):
        """Enable Archiving mode, to move the Ticket Channels to the set category once closed."""
        async with self.config.guild(ctx.guild).archive() as data:
            if yes_or_no is None:
                data["enabled"] = not data["enabled"]
                yes_or_no = data["enabled"]
            else:
                data["enabled"] = yes_or_no

        if yes_or_no:
            await ctx.send("Archiving mode is now enabled.")
        else:
            await ctx.send("Archiving mode is now disabled.")

    @settings.command()
    async def reports(self, ctx, channel: discord.TextChannel = None):
        """Set a channel to make a mini report in when a ticket is closed or opened.

        If left blank, this will disable reports."""
        saving = channel.id or 0
        await self.config.guild(ctx.guild).report.set(saving)

        if not channel:
            await ctx.send("Reporting has been disabled.")
        else:
            await ctx.send(f"Reporting channel has been set to {channel.mention}")

    @settings.command()
    async def enable(self, ctx, yes_or_no: Optional[bool] = None):
        """Starts listening for the set Reaction on the set Message to process tickets"""
        # We'll run through a test of all the settings to ensure everything is set properly

        # 1 - Ticket message is accessible and we can do what is needed with it
        channel_id, message_id = list(
            map(int, (await self.config.guild(ctx.guild).msg()).split("-"))
        )
        if channel_id == message_id == 0:
            await ctx.send(
                "Please set the message to listen on first with"
                f"`{ctx.prefix}reacticket settings setmsg`."
            )
            return

        try:
            message = await self.bot.get_channel(channel_id).fetch_message(message_id)
        except AttributeError:
            # Channel no longer exists
            await self.config.guild(ctx.guild).msg.set("0-0")
            await ctx.send(
                f"Please reset the message to listen on `{ctx.prefix}reacticket settings setmsg`."
                "\nReason: Channel has been deleted"
            )
            return
        except discord.NotFound:
            # Message no longer exists
            await self.config.guild(ctx.guild).msg.set("0-0")
            await ctx.send(
                f"Please reset the message to listen on `{ctx.prefix}reacticket settings setmsg`."
                "\nReason: Message has been deleted"
            )
            return
        except discord.Forbidden:
            # We don't have permission to read that message
            await ctx.send(
                "Please reconfigure my permissions in the set channel to allow me: "
                "Read Messages, Add Reactions, Manage Messages."
            )
            return

        if not message.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(
                "Please reconfigure my permissions in the set channel to allow me: "
                "Read Messages, Add Reactions, Manage Messages."
            )
            return

        # 2 - Check reaction is set properly
        emoji = await self.config.guild(ctx.guild).reaction()
        if emoji.isdigit():
            emoji = self.bot.get_emoji(int(emoji))
            if not emoji:
                await self.config.guild(ctx.guild).reaction.set("\N{ADMISSION TICKETS}")
                await ctx.send(
                    "Set custom emoji is invalid.  Ensure that the emoji still exists?\n"
                    "If you would like to bypass this and go with the default, "
                    "re-run this command."
                )
                return

        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await ctx.send(
                "Failed to react to set message with emoji.  "
                "Are you sure the emoji is valid and I have Add Reations permision?"
            )
            return

        # 3 - Category check
        category_id = await self.config.guild(ctx.guild).category()
        if not category_id:
            await ctx.send(
                "Please set the category to create ticket channels under with "
                f"`{ctx.prefix}reacticket settings category`."
            )
            return

        category = self.bot.get_channel(category_id)
        if not category:
            await ctx.send(
                "Please reset the category to create ticket channels under with "
                f"`{ctx.prefix}reacticket settings category`.\n"
                "Reason: Category has been deleted."
            )
            return

        if not category.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(
                "Please reconfigure my permissions in the set category to allow me"
                '"Manage Channels".'
            )
            return

        # 4 - Archive check (if enabled)
        archive = await self.config.guild(ctx.guild).archive()
        if archive["enabled"]:
            if not archive["category"]:
                await ctx.send(
                    "Archive mode is enabled but no category is set.  "
                    f"Please set one with `{ctx.prefix}reacticket settings archive category`."
                )
                return

            archive_category = self.bot.get_channel(archive["category"])
            if not archive_category:
                await ctx.send(
                    "Archive mode is enabled but set category does not exist.  "
                    f"Please reset it with `{ctx.prefix}reacticket settings archive category`."
                )
                return

            if not archive_category.permissions_for(ctx.guild.me).manage_channels:
                await ctx.send(
                    "Archive mode is enabled but I do not have permission to manage channels in "
                    "set category.  Please reconfigure my permissions to allow me to "
                    '"Manage Channels".'
                )
                return

        # 5 - Reporting channel (also if enabled)
        report = await self.config.guild(ctx.guild).report()
        if report != 0:
            report_channel = self.bot.get_channel(report)
            if not report_channel:
                await ctx.send(
                    "Reporting is enabled but the channel has been deleted.  "
                    f"Please reset it with `{ctx.prefix}reacticket settings report`."
                )

            if not report_channel.permissions_for(ctx.guild.me).send_messages:
                await ctx.send(
                    "Reporting is enabled but I do not have proper permissions.  "
                    "Please reconfigure my permissions to allow me Read and Send Messages."
                )
                return

        # Checks passed, let's cleanup a little bit and then enable
        await message.clear_reactions()
        await message.add_reaction(emoji)
        await self.config.guild(ctx.guild).enabled.set(True)

        await ctx.send("All checks passed.  Ticket system is now active.")

    @settings.command()
    async def disable(self, ctx):
        """Disable ticketing system"""
        await self.config.guild(ctx.guild).enabled.set(False)
        await ctx.send("Ticketing system disabled.")
