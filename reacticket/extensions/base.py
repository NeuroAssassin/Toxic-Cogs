from redbot.core.utils.mod import is_admin_or_superior
from discord.ext import commands
from typing import Dict, Optional, TYPE_CHECKING
import discord
import contextlib
import asyncio


from reacticket.extensions.abc import MixinMeta
from reacticket.extensions.mixin import reacticket

if discord.__version__ == "2.0.0a" or TYPE_CHECKING:
    from reacticket.extensions.views.queue import Queue


class ReacTicketBaseMixin(MixinMeta):
    async def report_close(self, ctx, ticket, author, guild_settings, reason):
        representing = author.mention if isinstance(author, discord.Member) else author
        channel = self.bot.get_channel(ticket["channel"])

        if guild_settings["report"] != 0:
            reporting_channel = self.bot.get_channel(guild_settings["report"])
            if reporting_channel:
                if await self.embed_requested(reporting_channel):
                    embed = discord.Embed(
                        title="Ticket Closed",
                        description=(
                            f"Ticket {channel.mention} created by "
                            f"{representing} has been closed by "
                            f"{ctx.author.mention}."
                        ),
                        color=await ctx.embed_color(),
                    )
                    if reason:
                        embed.add_field(name="Reason", value=reason)
                    if ticket["assigned"]:
                        moderator = getattr(
                            ctx.guild.get_member(ticket["assigned"]),
                            "mention",
                            "Unknown moderator",
                        )
                        embed.add_field(
                            name="Assigned moderator", value=moderator,
                        )

                    await reporting_channel.send(embed=embed)
                else:
                    message = (
                        f"Ticket {channel.mention} created by "
                        f"{representing} has been closed by "
                        f"{ctx.author.mention}."
                    )
                    if reason:
                        message += f"\n**Reason**: {reason}"

                    if ticket["assigned"]:
                        moderator = getattr(
                            ctx.guild.get_member(ticket["assigned"]),
                            "mention",
                            "Unknown moderator",
                        )
                        message += f"\nAssigned moderator: {moderator}"
                    await reporting_channel.send(
                        message, allowed_mentions=discord.AllowedMentions.none()
                    )

        if guild_settings["dm"] and isinstance(author, discord.Member):
            embed = discord.Embed(
                title="Ticket Closed",
                description=(
                    f"Your ticket {channel.mention} has been closed by {ctx.author.mention}."
                ),
                color=await ctx.embed_color(),
            )
            if reason:
                embed.add_field(name="Reason", value=reason)
            with contextlib.suppress(discord.HTTPException):
                await author.send(embed=embed)

    async def process_closed_ticket(
        self, ctx, guild_settings, channel, archive, author, added_users
    ):
        representing = author.mention if isinstance(author, discord.Member) else author
        if guild_settings["archive"]["enabled"] and channel and archive:
            for user in added_users:
                with contextlib.suppress(discord.HTTPException):
                    if user:
                        await channel.set_permissions(
                            user, send_messages=False, read_messages=True
                        )

            destination = channel or ctx

            await destination.send(
                f"Ticket {channel.mention} for {representing} has been closed. "
                "Channel will be moved to archive in one minute.",
                allowed_mentions=discord.AllowedMentions.none(),
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
                    for role_id in guild_settings["supportroles"]
                    if ctx.guild.get_role(role_id)
                ]

                all_roles = admin_roles + support_roles
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.guild.me: discord.PermissionOverwrite(
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
                await destination.send(f"Failed to move to archive: {str(e)}")
        else:
            destination = channel or ctx

            if channel:
                for user in added_users:
                    with contextlib.suppress(discord.HTTPException):
                        if user:
                            await channel.set_permissions(
                                user, send_messages=False, read_messages=True
                            )
            await destination.send(
                f"Ticket {channel.mention} for {representing} has been closed. "
                "Channel will be deleted in one minute, if exists.",
                allowed_mentions=discord.AllowedMentions.none(),
            )

            await asyncio.sleep(60)

            if channel:
                try:
                    await channel.delete()
                except discord.HTTPException:
                    with contextlib.suppress(discord.HTTPException):
                        await destination.send(
                            'Failed to delete channel.  Please ensure I have "Manage Channels" '
                            "permission in the category."
                        )

    @reacticket.command()
    async def close(self, ctx, *, reason=None):
        """Closes the created ticket.

        If run by a normal user, this will default to the user.
        If run by an admin or support team, this will check the channel."""
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
            author_id = author.id
        elif is_admin:
            # Let's try to get the current channel and get the author
            # If not, we'll default to ctx.author
            inverted = {}
            for author_id, tickets in guild_settings["created"].items():
                for ticket in tickets:
                    inverted[ticket["channel"]] = author_id
            try:
                author = ctx.guild.get_member(int(inverted[ctx.channel.id]))
                if author:
                    author_id = author.id
                else:
                    author_id = int(inverted[ctx.channel.id])
            except KeyError:
                author = ctx.author
                author_id = author.id

        if str(author_id) not in guild_settings["created"]:
            await ctx.send("That user does not have an open ticket.")
            return

        index = None
        if not guild_settings["created"][str(author_id)]:
            await ctx.send("You don't have any open tickets.")
            return
        elif len(guild_settings["created"][str(author_id)]) == 1:
            index = 0
        else:
            for i, ticket in enumerate(guild_settings["created"][str(author_id)]):
                if ticket["channel"] == ctx.channel.id:
                    index = i
                    break

            if index is None:
                await ctx.send(
                    "You have multiple tickets open.  "
                    "Please run this command in the ticket channel you wish to close."
                )
                return

        ticket = guild_settings["created"][str(author_id)][index]
        channel = self.bot.get_channel(ticket["channel"])
        archive = self.bot.get_channel(guild_settings["archive"]["category"])
        added_users = [user for u in ticket["added"] if (user := ctx.guild.get_member(u))]
        added_users.append(author)

        # Again, to prevent race conditions...
        async with self.config.guild(ctx.guild).created() as created:
            del created[str(author_id)][index]

        await self.report_close(
            ctx=ctx,
            ticket=ticket,
            author=author or author_id,
            guild_settings=guild_settings,
            reason=reason,
        )

        await self.process_closed_ticket(
            ctx=ctx,
            guild_settings=guild_settings,
            channel=channel,
            archive=archive,
            author=author or author_id,
            added_users=added_users,
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
            author_id = author.id
        elif is_admin:
            # Since the author isn't specified, and it's an admin, we need to guess on who
            # the author is
            inverted = {}
            for author_id, tickets in guild_settings["created"].items():
                for ticket in tickets:
                    inverted[ticket["channel"]] = author_id
            try:
                author = ctx.guild.get_member(int(inverted[ctx.channel.id]))
                if author:
                    author_id = author.id
                else:
                    author_id = int(inverted[ctx.channel.id])
            except KeyError:
                author = ctx.author
                author_id = author.id

        index = None

        if not guild_settings["created"][str(author_id)]:
            await ctx.send("You don't have any open tickets.")
            return
        elif len(guild_settings["created"][str(author_id)]) == 1:
            index = 0
        else:
            for i, ticket in enumerate(guild_settings["created"][str(author_id)]):
                if ticket["channel"] == ctx.channel.id:
                    index = i
                    break

            if index is None:
                await ctx.send(
                    "You have multiple tickets open.  "
                    "Please run this command in the ticket channel you wish to edit."
                )
                return

        channel = self.bot.get_channel(guild_settings["created"][str(author_id)][index]["channel"])

        if user.id in guild_settings["created"][str(author_id)][index]["added"]:
            await ctx.send("That user is already added.")
            return

        adding_is_admin = await is_admin_or_superior(self.bot, user) or any(
            [ur.id in guild_settings["supportroles"] for ur in user.roles]
        )

        if adding_is_admin:
            await ctx.send("You cannot add a user in support or admin team.")
            return

        channel = self.bot.get_channel(guild_settings["created"][str(author_id)][index]["channel"])
        if not channel:
            await ctx.send("The ticket channel has been deleted.")
            return

        try:
            await channel.set_permissions(user, send_messages=True, read_messages=True)
        except discord.Forbidden:
            await ctx.send(
                "The Manage Permissions channel for me has been removed.  "
                "I am unable to modify this ticket."
            )
            return

        async with self.config.guild(ctx.guild).created() as created:
            created[str(author_id)][index]["added"].append(user.id)

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
            author_id = author.id
        elif is_admin:
            # Since the author isn't specified, and it's an admin, we need to guess on who
            # the author is
            inverted = {}
            for author_id, tickets in guild_settings["created"].items():
                for ticket in tickets:
                    inverted[ticket["channel"]] = author_id
            try:
                author = ctx.guild.get_member(int(inverted[ctx.channel.id]))
                if author:
                    author_id = author.id
                else:
                    author_id = int(inverted[ctx.channel.id])
            except KeyError:
                author = ctx.author
                author_id = author.id

        index = None

        if not guild_settings["created"][str(author_id)]:
            await ctx.send("You don't have any open tickets.")
            return
        elif len(guild_settings["created"][str(author_id)]) == 1:
            index = 0
        else:
            for i, ticket in enumerate(guild_settings["created"][str(author_id)]):
                if ticket["channel"] == ctx.channel.id:
                    index = i
                    break

            if index is None:
                await ctx.send(
                    "You have multiple tickets open.  "
                    "Please run this command in the ticket channel you wish to edit."
                )
                return

        if user.id not in guild_settings["created"][str(author_id)][index]["added"]:
            await ctx.send("That user is not added.")
            return

        removing_is_admin = await is_admin_or_superior(self.bot, user) or any(
            [ur.id in guild_settings["supportroles"] for ur in user.roles]
        )

        if removing_is_admin:
            await ctx.send("You cannot remove a user in support or admin team.")
            return

        channel = self.bot.get_channel(guild_settings["created"][str(author_id)][index]["channel"])
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
            created[str(author_id)][index]["added"].remove(user.id)

        await ctx.send(f"{user.mention} has been removed from the ticket.")

    @reacticket.command(name="name")
    async def ticket_name(self, ctx, *, name: str):
        """Rename the ticket in scope."""
        guild_settings = await self.config.guild(ctx.guild).all()
        is_admin = await is_admin_or_superior(self.bot, ctx.author) or any(
            [ur.id in guild_settings["supportroles"] for ur in ctx.author.roles]
        )
        must_be_admin = not guild_settings["usercanname"]

        if not is_admin and must_be_admin:
            await ctx.send("Only Administrators can rename tickets.")
            return
        elif not is_admin:
            author = ctx.author
            author_id = author.id
        elif is_admin:
            # Since the author isn't specified, and it's an admin, we need to guess on who
            # the author is
            inverted = {}
            for author_id, tickets in guild_settings["created"].items():
                for ticket in tickets:
                    inverted[ticket["channel"]] = author_id
            try:
                author = ctx.guild.get_member(int(inverted[ctx.channel.id]))
                if author:
                    author_id = author.id
                else:
                    author_id = int(inverted[ctx.channel.id])
            except KeyError:
                author = ctx.author
                author_id = author.id

        if str(author_id) not in guild_settings["created"]:
            await ctx.send("You don't have any open tickets.")
            return

        index = None

        if not guild_settings["created"][str(author_id)]:
            await ctx.send("You don't have any open tickets.")
            return
        elif len(guild_settings["created"][str(author_id)]) == 1:
            index = 0
        else:
            for i, ticket in enumerate(guild_settings["created"][str(author_id)]):
                if ticket["channel"] == ctx.channel.id:
                    index = i
                    break

            if index is None:
                await ctx.send(
                    "You have multiple tickets open.  "
                    "Please run this command in the ticket channel you wish to edit."
                )
                return

        channel = self.bot.get_channel(guild_settings["created"][str(author_id)][index]["channel"])
        if not channel:
            await ctx.send("The ticket channel has been deleted.")
            return

        if len(name) > 99:
            await ctx.send("Channel names must be less 100 characters")
            return

        try:
            await channel.edit(name=name)
        except discord.Forbidden:
            await ctx.send(
                "The Manage Channels channel for me has been removed.  "
                "I am unable to modify this ticket."
            )
            return

        await ctx.send("The ticket has been renamed.")

    async def lock_ticket(self, ctx, ticket):
        channel = ctx.guild.get_channel(ticket["channel"])
        author = ctx.guild.get_member(ticket["user"])
        added_users = [user for u in ticket["added"] if (user := ctx.guild.get_member(u))]
        added_users.append(author)

        for user in added_users:
            with contextlib.suppress(discord.HTTPException):
                if user:
                    await channel.set_permissions(user, send_messages=False, read_messages=True)

        await channel.send(
            (
                "This ticket has been locked by the Administrators.  It can be unlocked by using "
                f"`{ctx.prefix}reacticket unlock {channel.mention}`, or through the queue."
            )
        )

        async with self.config.guild(ctx.guild).created() as created:
            for index, i_ticket in enumerate(created[str(author.id)]):
                if i_ticket["channel"] == ticket["channel"]:
                    created[str(author.id)][index]["locked"] = True
                    break

    async def unlock_ticket(self, ctx, ticket):
        channel = ctx.guild.get_channel(ticket["channel"])
        author = ctx.guild.get_member(ticket["user"])
        added_users = [user for u in ticket["added"] if (user := ctx.guild.get_member(u))]
        added_users.append(author)

        for user in added_users:
            with contextlib.suppress(discord.HTTPException):
                if user:
                    await channel.set_permissions(user, send_messages=True, read_messages=True)

        await channel.send("This ticket has been unlocked by the Administrators.")

        async with self.config.guild(ctx.guild).created() as created:
            for index, i_ticket in enumerate(created[str(author.id)]):
                if i_ticket["channel"] == ticket["channel"]:
                    created[str(author.id)][index]["locked"] = False
                    break

    def is_support_or_superior():
        async def predicate(ctx):
            guild_settings = await ctx.bot.get_cog("ReacTicket").config.guild(ctx.guild).all()
            is_admin = await is_admin_or_superior(ctx.bot, ctx.author) or any(
                [ur.id in guild_settings["supportroles"] for ur in ctx.author.roles]
            )
            if is_admin:
                return True

            return False

        return commands.check(predicate)

    @is_support_or_superior()
    @reacticket.command(aliases=["unlock"])
    async def lock(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Lock the specified ticket channel.  If no channel is provided, defaults to current.

        Note: You must have a ReacTicket Support Role or a Red Admin Role to run this."""
        if channel is None:
            channel = ctx.channel

        created = await self.config.guild(ctx.guild).created()
        selected_ticket = None
        for user_id, user_tickets in created.items():
            for ticket in user_tickets:
                if ticket["channel"] == channel.id:
                    ticket["user"] = int(user_id)
                    selected_ticket = ticket
                    break
            if selected_ticket:
                break

        if not selected_ticket:
            await ctx.send(f"Failed to find a ticket associated with {channel.mention}.")
            return

        if selected_ticket["locked"]:
            await self.unlock_ticket(ctx, selected_ticket)
        else:
            await self.lock_ticket(ctx, selected_ticket)

        await ctx.tick()

    async def assign_moderator(
        self, guild: discord.Guild, ticket: Dict, moderator: discord.Member
    ):
        channel = guild.get_channel(ticket["channel"])
        author = guild.get_member(ticket["user"])
        if channel:
            await channel.send(
                f"{moderator.mention} has been assigned as the Moderator for this ticket."
            )

        async with self.config.guild(guild).created() as created:
            for index, i_ticket in enumerate(created[str(author.id)]):
                if i_ticket["channel"] == ticket["channel"]:
                    created[str(author.id)][index]["assigned"] = moderator.id
                    break

    @is_support_or_superior()
    @reacticket.command(aliases=["moderator", "mod"])
    async def assign(
        self, ctx, moderator: discord.Member, ticket: Optional[discord.TextChannel] = None
    ):
        if not ticket:
            ticket = ctx.channel

        guild_settings = await self.config.guild(ctx.guild).all()

        inverted = {}
        for author_id, tickets in guild_settings["created"].items():
            for uticket in tickets:
                uticket["user"] = int(author_id)
                inverted[uticket["channel"]] = uticket

        try:
            ticket = inverted[ticket.id]
        except KeyError:
            await ctx.send(f"Failed to find a ticket associated with {ticket.mention}.")
            return

        if not (
            await is_admin_or_superior(self.bot, moderator)
            or any([ur.id in guild_settings["supportroles"] for ur in moderator.roles])
        ):
            await ctx.send(
                "The moderator being assigned must be a Red Administrator "
                "or have a ReacTicket Support Role."
            )
            return

        if moderator.id == ticket["assigned"]:
            await ctx.send(
                f"{moderator.mention} is already the Assigned Moderator for the ticket.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        if moderator.id == ticket["user"]:
            await ctx.send(
                f"{moderator.mention} cannot be assigned to their own ticket.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        await self.assign_moderator(ctx.guild, ticket, moderator)
        await ctx.tick()

    def sort_tickets(self, unsorted):
        tickets = []
        for user_id, user_tickets in unsorted.items():
            for ticket in user_tickets:
                ticket["user"] = int(user_id)
                tickets.append(ticket)

        if not tickets:
            raise ValueError

        tickets.sort(key=lambda x: x["opened"], reverse=True)

        complete = []
        index = -1
        counter = 0
        for ticket in tickets:
            if counter % 5 == 0:
                index += 1
                complete.append([])

            complete[index].append(ticket)
            counter += 1

        return complete

    def on_discord_alpha():
        def predicate(ctx):
            return discord.__version__ == "2.0.0a"

        return commands.check(predicate)

    @on_discord_alpha()
    @is_support_or_superior()
    @commands.bot_has_permissions(embed_links=True)
    @reacticket.command(aliases=["tickets"])
    async def queue(self, ctx):
        """List, modify and close tickets sorted based upon when they were opened"""
        unsorted_tickets = await self.config.guild(ctx.guild).created()

        try:
            complete = self.sort_tickets(unsorted_tickets)
        except ValueError:
            embed = discord.Embed(
                title="Open tickets",
                description="No tickets are currently open.",
                color=await ctx.embed_color(),
            )
            await ctx.send(embed=embed)
            return

        queue = Queue(ctx, complete)
        await queue.build_embed()
        message = await ctx.send(embed=queue.embed, view=queue)
        queue.set_message(message)
