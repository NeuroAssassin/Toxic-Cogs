from redbot.core.utils.predicates import ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions
from typing import Optional
import discord
import contextlib

from reacticket.extensions.abc import MixinMeta
from reacticket.extensions.mixin import settings


class ReacTicketCloseSettingsMixin(MixinMeta):
    @settings.group()
    async def closesettings(self, ctx):
        """Control what actions occur when a ticket is closed"""
        pass

    @closesettings.group()
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

    @closesettings.command()
    async def reports(self, ctx, channel: discord.TextChannel = None):
        """Set a channel to make a mini report in when a ticket is closed or opened.

        If left blank, this will disable reports."""
        saving = getattr(channel, "id", 0)
        await self.config.guild(ctx.guild).report.set(saving)

        if not channel:
            await ctx.send("Reporting has been disabled.")
        else:
            await ctx.send(f"Reporting channel has been set to {channel.mention}")

    @closesettings.command()
    async def dm(self, ctx, yes_or_no: bool = None):
        """Set whether or not to send a DM to the ticket author on ticket close."""
        if yes_or_no is None:
            yes_or_no = not await self.config.guild(ctx.guild).dm()

        await self.config.guild(ctx.guild).dm.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Users will now be DMed a message when their ticket is closed.")
        else:
            await ctx.send("Users will no longer be DMed a message when their ticket is closed.")

    @closesettings.command(name="closeonleave")
    async def close_ticket_on_leave(self, ctx, toggle: Optional[bool] = None):
        """Set whether to automatically close tickets if the ticket author leaves."""
        if toggle is None:
            toggle = not await self.config.guild(ctx.guild).closeonleave()

        await self.config.guild(ctx.guild).closeonleave.set(toggle)
        if toggle:
            await ctx.send(
                "Tickets will now be automatically closed if the author leaves the server."
            )
        else:
            await ctx.send("Tickets will be kept open even if the author leaves the server")

    @closesettings.command(name="prune", aliases=["cleanup", "purge"])
    async def ticket_channel_prune(self, ctx):
        """Clean out channels under the archive category.

        Pass a user to only delete the channels created by that user instead.

        WARNING: This will remove ALL channels unless otherwise specified!"""
        category = self.bot.get_channel((await self.config.guild(ctx.guild).archive())["category"])
        if not category:
            await ctx.send("Your archive category no longer exists!")
            return

        channels = category.text_channels
        message = await ctx.send(
            "Are you sure you want to remove all archived ticket channels?  "
            f"This will delete {len(channels)} Text Channels."
        )

        start_adding_reactions(message, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(message, ctx.author)
        await self.bot.wait_for("reaction_add", check=pred)
        if pred.result is True:
            progress = await ctx.send("Purging text channels...")
            for channel in channels:
                try:
                    await channel.delete()
                except discord.Forbidden:
                    await ctx.send(
                        "I do not have permission to delete those text channels.  "
                        'Make sure I have both "Manage Channels" and "View Channels".'
                    )
                    return
                except discord.HTTPException:
                    continue

            with contextlib.suppress(discord.HTTPException):
                await progress.edit(content="Channels successfully purged.")
        else:
            await ctx.send("Channel purge cancelled.")
