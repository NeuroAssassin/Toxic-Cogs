from typing import Union, Optional
import discord
import copy

from reacticket.extensions.abc import MixinMeta
from reacticket.extensions.mixin import settings


class ReacTicketBaseSettingsMixin(MixinMeta):
    @settings.group(name="precreationsettings")
    async def pre_creation_settings(self, ctx):
        """Control the actions that are checked/occur before ticket is created"""
        pass

    @pre_creation_settings.command()
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

    @pre_creation_settings.command()
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

    @pre_creation_settings.command()
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

    @settings.group(name="postcreationsettings")
    async def post_creation_settings(self, ctx):
        """Control the actions that occur post the ticket being created"""
        pass

    @post_creation_settings.command(name="creationmessage", aliases=["openmessage"])
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

    @post_creation_settings.command()
    async def category(self, ctx, category: discord.CategoryChannel):
        """Set the category to create ticket channels under."""
        if not category.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(
                'I require "Manage Channels" permissions in that category to execute that command.'
            )
            return

        await self.config.guild(ctx.guild).category.set(category.id)
        await ctx.send(f"Ticket channels will now be created in the {category.name} category")

    @post_creation_settings.command()
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
    async def enable(self, ctx, yes_or_no: Optional[bool] = None):
        """Starts listening for the set Reaction on the set Message to process tickets"""
        # We'll run through a test of all the settings to ensure everything is set properly

        # Before we get started to it, we'll check if the bot has Administrator permissions
        # NOTE for anyone reading: Do not make your cogs require Admin!  The only reason this is
        # happening is because Discord decided to lock MANAGE_PERMISSIONS behind Admin
        # (which is bullshit), therefore, I have to require it.  I would really rather not.
        if not ctx.channel.permissions_for(ctx.guild.me).administrator:
            await ctx.send(
                "I require Administrator permission to start the ReacTicket system.  Note that "
                "under normal circumstances this would not be required, however Discord has "
                "changed how permissions operate with channel overwrites, and the "
                "MANAGE_PERMISSIONS permission requires Administrator privilege."
            )
            return

        # 1 - Ticket message is accessible and we can do what is needed with it
        channel_id, message_id = list(
            map(int, (await self.config.guild(ctx.guild).msg()).split("-"))
        )
        if channel_id == message_id == 0:
            await ctx.send(
                "Please set the message to listen on first with"
                f"`{ctx.prefix}reacticket settings precreationsettings`."
            )
            return

        try:
            message = await self.bot.get_channel(channel_id).fetch_message(message_id)
        except AttributeError:
            # Channel no longer exists
            await self.config.guild(ctx.guild).msg.set("0-0")
            await ctx.send(
                f"Please reset the message to listen on `{ctx.prefix}reacticket settings precreationsettings setmsg`."
                "\nReason: Channel has been deleted"
            )
            return
        except discord.NotFound:
            # Message no longer exists
            await self.config.guild(ctx.guild).msg.set("0-0")
            await ctx.send(
                f"Please reset the message to listen on `{ctx.prefix}reacticket settings precreationsettings setmsg`."
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
                f"`{ctx.prefix}reacticket settings postcreationsettings category`."
            )
            return

        category = self.bot.get_channel(category_id)
        if not category:
            await ctx.send(
                "Please reset the category to create ticket channels under with "
                f"`{ctx.prefix}reacticket settings postcreationsettings category`.\n"
                "Reason: Category has been deleted."
            )
            return

        # 4 - Archive check (if enabled)
        archive = await self.config.guild(ctx.guild).archive()
        if archive["enabled"]:
            if not archive["category"]:
                await ctx.send(
                    "Archive mode is enabled but no category is set.  "
                    f"Please set one with `{ctx.prefix}reacticket settings closesettings archive category`."
                )
                return

            archive_category = self.bot.get_channel(archive["category"])
            if not archive_category:
                await ctx.send(
                    "Archive mode is enabled but set category does not exist.  "
                    f"Please reset it with `{ctx.prefix}reacticket settings closesettings archive category`."
                )
                return

        # 5 - Reporting channel (also if enabled)
        report = await self.config.guild(ctx.guild).report()
        if report != 0:
            report_channel = self.bot.get_channel(report)
            if not report_channel:
                await ctx.send(
                    "Reporting is enabled but the channel has been deleted.  "
                    f"Please reset it with `{ctx.prefix}reacticket settings closesettings reports`."
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
