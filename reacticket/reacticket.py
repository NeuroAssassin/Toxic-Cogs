from redbot.core.utils.mod import is_admin_or_superior
from redbot.core.bot import Red
from redbot.core import commands, checks, Config
from typing import Union, Optional
import discord
import contextlib
import asyncio


class ReacTicket(commands.Cog):
    def __init__(self, bot: Red):
        self.bot: Red = bot

        default_guild = {
            "reaction": "\N{ADMISSION TICKETS}",
            "usercanclose": False,
            "msg": "0-0",
            "category": 0,
            "enabled": False,
            "created": {},
        }

        self.config = Config.get_conf(self, identifier=473541068378341376, force_registration=True)
        self.config.register_guild(**default_guild)

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

        user = guild.get_member(payload.user_id)
        admin_roles = [
            guild.get_role(role_id)
            for role_id in (await self.bot._config.guild(guild).admin_role())
            if guild.get_role(role_id)
        ]

        can_read = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: can_read,
            user: can_read,
        }
        for role in admin_roles:
            overwrites[role] = can_read

        created_channel = await category.create_text_channel(
            f"ticket-{payload.user_id}", overwrites=overwrites
        )
        if guild_settings["usercanclose"]:
            await created_channel.send(
                f"Ticket created for {user.display_name}\nTo close this, "
                f"Administrators or {user.display_name} may run `[p]reacticket close`."
            )
        else:
            await created_channel.send(
                f"Ticket created for {user.display_name}\n"
                "Only Administrators may close this by running `[p]reacticket close`."
            )

        # To prevent race conditions...
        async with self.config.guild(guild).created() as created:
            created[payload.user_id] = created_channel.id

        # If removing the reaction fails... eh
        with contextlib.suppress(discord.HTTPException):
            message = await self.bot.get_channel(payload.channel_id).fetch_message(
                payload.message_id
            )
            await message.remove_reaction(payload.emoji, member=user)

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
        is_admin = await is_admin_or_superior(self.bot, ctx.author)
        must_be_admin = not guild_settings["usercanclose"]

        if not is_admin and must_be_admin:
            await ctx.send("Only Administrators can close tickets.")
            return
        elif not is_admin or (is_admin and not author):
            author = ctx.author  # no u

        if str(author.id) not in guild_settings["created"]:
            await ctx.send("That user does not have an open ticket.")
            return

        channel = self.bot.get_channel(guild_settings["created"][str(author.id)])

        # Again, to prevent race conditions...
        async with self.config.guild(ctx.guild).created() as created:
            del created[str(author.id)]

        await ctx.send(
            f"Ticket for {author.display_name} has been closed.  Channel will be deleted in one minute, if exists."
        )

        await asyncio.sleep(60)

        if channel:
            try:
                await channel.delete()
            except discord.HTTPException:
                await ctx.send(
                    'Failed to delete channel.  Please ensure I have "Manage Channels" '
                    "permission in the category."
                )

    @checks.admin()
    @reacticket.group(invoke_without_command=True)
    async def settings(self, ctx):
        """Manage settings for ReacTicket"""
        guild_settings = await self.config.guild(ctx.guild).all()
        channel_id, message_id = list(map(int, guild_settings["msg"].split("-")))
        await ctx.send(
            "```ini\n"
            f"[Channel ID]:       {getattr(self.bot.get_channel(channel_id), 'name', 'Not set')}\n"
            f"[Message ID]:       {message_id}\n"
            f"[Reaction]:         {guild_settings['reaction']}\n"
            f"[User-closable]:    {guild_settings['usercanclose']}\n"
            f"[Ticket category]:  {getattr(self.bot.get_channel(guild_settings['category']), 'name', 'Not set')}\n"
            f"[Enabled]:          {guild_settings['enabled']}\n"
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
    async def category(self, ctx, category: discord.CategoryChannel):
        """Set the category to create ticket channels under."""
        if not category.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(
                'I require "Manage Channels" permissions in that category to execute that command.'
            )
            return

        await self.config.guild(ctx.guild).category.set(category.id)
        await ctx.send(f"Ticket channels will now be created in the {category.name} category")

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
