from redbot.core.utils.mod import is_admin_or_superior
import discord
import contextlib
import asyncio


from reacticket.extensions.abc import MixinMeta
from reacticket.extensions.mixin import reacticket


class ReacTicketBaseMixin(MixinMeta):
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

        channel = self.bot.get_channel(guild_settings["created"][str(author_id)][index]["channel"])
        archive = self.bot.get_channel(guild_settings["archive"]["category"])
        added_users = [
            user
            for u in guild_settings["created"][str(author_id)][index]["added"]
            if (user := ctx.guild.get_member(u))
        ]
        added_users.append(author)

        # Again, to prevent race conditions...
        async with self.config.guild(ctx.guild).created() as created:
            del created[str(author_id)][index]

        if guild_settings["report"] != 0:
            reporting_channel = self.bot.get_channel(guild_settings["report"])
            if reporting_channel:
                if await self.embed_requested(reporting_channel):
                    embed = discord.Embed(
                        title="Ticket Closed",
                        description=(
                            f"Ticket {channel.mention} created by "
                            f"{author.mention if author else author_id} "
                            f"has been closed by {ctx.author.mention}."
                        ),
                        color=await ctx.embed_color(),
                    )
                    if reason:
                        embed.add_field(name="Reason", value=reason)
                    await reporting_channel.send(embed=embed)
                else:
                    message = (
                        f"Ticket {channel.mention} created by "
                        f"{str(author) if author else author_id} "
                        f"has been closed by {str(ctx.author)}."
                    )
                    if reason:
                        message += f"\n**Reason**: {reason}"

                    await reporting_channel.send(message)

        if guild_settings["dm"] and author:
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

        if guild_settings["archive"]["enabled"] and channel and archive:
            for user in added_users:
                with contextlib.suppress(discord.HTTPException):
                    if user:
                        await channel.set_permissions(
                            user, send_messages=False, read_messages=True
                        )
            await ctx.send(
                f"Ticket {channel.mention} for {author.display_name if author else author_id} "
                "has been closed.  Channel will be moved to archive in one minute."
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
                await ctx.send(f"Failed to move to archive: {str(e)}")
        else:
            if channel:
                for user in added_users:
                    with contextlib.suppress(discord.HTTPException):
                        if user:
                            await channel.set_permissions(
                                user, send_messages=False, read_messages=True
                            )
            await ctx.send(
                f"Ticket {channel.mention} for {author.display_name if author else author_id} "
                "has been closed.  Channel will be deleted in one minute, if exists."
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

        try:
            await channel.edit(name=name)
        except discord.Forbidden:
            await ctx.send(
                "The Manage Channels channel for me has been removed.  "
                "I am unable to modify this ticket."
            )
            return

        await ctx.send("The ticket has been renamed.")
