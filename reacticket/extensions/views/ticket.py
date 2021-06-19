from redbot.core.utils.chat_formatting import humanize_list
from redbot.core.utils.mod import is_admin_or_superior
from redbot.core.commands.context import Context
from typing import Dict, Optional, TYPE_CHECKING
from datetime import datetime
import discord
import asyncio

from reacticket.extensions.views.confirmation import Confirmation
from reacticket.extensions.views.alert import Alert

if TYPE_CHECKING:
    from reacticket.extensions.views.queue import Queue
    from reacticket.reacticket import ReacTicket


class Ticket(discord.ui.View):
    def __init__(self, ctx: Context, ticket: Dict, parent: "Queue"):
        self.ctx: Context = ctx
        self.ticket: Dict = ticket
        self.parent: Queue = parent

        self.embed: Optional[discord.Embed] = None
        self.timed_out: bool = True
        self.repeat: bool = False

        super().__init__()

        url = "https://discord.com/channels/{guild_id}/{channel_id}".format(
            guild_id=self.ctx.guild.id, channel_id=self.ticket["channel"]
        )

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link, label="Jump to Ticket", url=url, row=1
            )
        )

        self.refresh_buttons()

    def refresh_buttons(self):
        for child in self.children:
            if child.custom_id == self.assign_moderator.custom_id:
                if self.ticket["assigned"]:
                    child.label = "Re-Assign Moderator"
                    child.style = discord.ButtonStyle.secondary
            elif child.custom_id == self.toggle_ticket_lock.custom_id:
                if self.ticket["locked"]:
                    child.label = "Unlock Ticket"
                    child.emoji = "\N{OPEN LOCK}"

    async def build_embed(self):
        self.embed = discord.Embed(
            title="Queued Ticket", description="", color=await self.ctx.embed_color()
        )

        user = getattr(self.ctx.guild.get_member(self.ticket["user"]), "mention", "Removed user")
        self.embed.add_field(name="Ticket Author", value=user, inline=True)

        added_users = []
        for user in self.ticket["added"]:
            added_users.append(getattr(self.ctx.guild.get_member(user), "mention", "Removed user"))
        self.embed.add_field(
            name="Ticket Members",
            value=humanize_list(added_users) or "This ticket does not have any members",
            inline=True,
        )

        moderator = "No moderator assigned"
        if self.ticket["assigned"]:
            moderator = getattr(
                self.ctx.guild.get_member(self.ticket["assigned"]), "mention", "Removed user"
            )
        self.embed.add_field(name="Ticket Moderator", value=moderator, inline=True)

        timestamp = datetime.fromtimestamp(self.ticket["opened"]).strftime(
            "%B %d, %Y at %H:%M UTC"
        )
        self.embed.add_field(name="Ticket Creation Date", value=timestamp, inline=True)

    @discord.ui.button(
        label="Assign Moderator", style=discord.ButtonStyle.primary, emoji="\N{SHIELD}",
    )
    async def assign_moderator(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        prompt = discord.Embed(
            title="Assign Moderator",
            description=(
                "Mention or provide user ID of the Moderator you would like to "
                "assign to this ticket. They must be a Red Admin or have a ReacTicket "
                "Support Role, and not be the author of the ticket."
            ),
            color=await self.ctx.embed_color(),
        )
        # TODO: uncomment
        # await interaction.response.edit_message(embed=prompt, view=None)
        await self.parent.original.edit(embed=prompt, view=None)

        def check(message):
            return (
                message.author.id == self.ctx.author.id
                and message.channel.id == self.ctx.channel.id
                and (
                    len(message.mentions) == 1
                    or message.content.isdigit()
                    or message.content.lower() == "cancel"
                )
            )

        try:
            user_response: discord.Message = await self.ctx.bot.wait_for(
                "message", check=check, timeout=60.0
            )
        except asyncio.TimeoutError:
            self.timed_out = False
            self.repeat = True
            self.stop()
            return

        moderator = None
        alert = None

        if user_response.content.lower() == "cancel":
            self.timed_out = False
            self.repeat = True
            self.stop()
            return
        elif user_response.mentions:
            moderator = user_response.mentions[0]
        else:
            moderator = self.ctx.guild.get_member(int(user_response.content))
            if not moderator:
                # In the future we'll keep this until the end, however I stop this here
                # because I want to avoid accessing config if I don't have to
                alert = Alert(
                    title="Failed to Assign Moderator",
                    description="I failed to find a Moderator with that ID.",
                    color=await self.ctx.embed_color(),
                )
                await self.parent.original.edit(**alert.send())
                await alert.wait()

                self.timed_out = False
                self.repeat = True
                self.stop()
                return

        ctx = self.ctx
        cog: ReacTicket = ctx.cog

        guild_settings = await cog.config.guild(ctx.guild).all()

        if not (
            await is_admin_or_superior(ctx.bot, moderator)
            or any([ur.id in guild_settings["supportroles"] for ur in moderator.roles])
        ):
            alert = Alert(
                title="Failed to Assign Moderator",
                description="The specified user is not a Red Admin or ReacTicket Support",
                color=await ctx.embed_color(),
            )
        elif moderator.id == self.ticket["assigned"]:
            alert = Alert(
                title="Failed to Assign Moderator",
                description="The specified user is not a Red Admin or ReacTicket Support",
                color=await ctx.embed_color(),
            )
        elif moderator.id == self.ticket["user"]:
            alert = Alert(
                title="Failed to Assign Moderator",
                description="The specified user cannot be assigned to their own ticket.",
                color=await ctx.embed_color(),
            )

        if not alert:
            await cog.assign_moderator(ctx.guild, self.ticket, moderator)
            self.ticket["assigned"] = moderator.id

            alert = Alert(
                title="Moderator Assigned to Ticket",
                description="Successfully assigned moderator to specified ticket.",
                color=await ctx.embed_color(),
            )

        await self.parent.original.edit(**alert.send())
        await alert.wait()

        self.timed_out = False
        self.repeat = True
        self.stop()
        return

    @discord.ui.button(
        label="Add/Remove Ticket Member",
        style=discord.ButtonStyle.secondary,
        emoji="\N{BUSTS IN SILHOUETTE}",
    )
    async def ar_member(self, button: discord.ui.Button, interaction: discord.Interaction):
        # TODO: remove
        await interaction.response.defer()
        prompt = discord.Embed(
            title="Add/Remove Ticket Member",
            description=(
                "Mention or provide user ID of the Guild Member you would like to "
                "add to/remove from this ticket. To add multiple users using IDs, "
                "place a space between each user.  Type 'cancel' to cancel."
            ),
            color=await self.ctx.embed_color(),
        )

        # TODO: uncomment
        # await interaction.response.edit_message(embed=prompt, view=None)
        await self.parent.original.edit(embed=prompt, view=None)

        def check(message):
            return (
                message.author.id == self.ctx.author.id
                and message.channel.id == self.ctx.channel.id
                and (
                    message.mentions
                    or message.content.replace(" ", "").isdigit()
                    or message.content.lower() == "cancel"
                )
            )

        try:
            user_response = await self.ctx.bot.wait_for("message", check=check, timeout=60.0)
        except asyncio.TimeoutError:
            self.timed_out = False
            self.repeat = True
            self.stop()
            return

        ctx = self.ctx
        cog = ctx.cog

        will_process = []
        added = []
        removed = []
        failed = []

        if user_response.content.lower() == "cancel":
            self.timed_out = False
            self.repeat = True
            self.stop()
            return
        elif user_response.mentions:
            will_process = user_response.mentions
        else:
            for uid in user_response.content.split(" "):
                if uid.isdigit():
                    user = ctx.guild.get_member(int(uid))
                    if user:
                        will_process.append(user)
                    else:
                        failed.append(user)

        channel = ctx.guild.get_channel(self.ticket["channel"])
        support = await cog.config.guild(ctx.guild).supportroles()
        exit_early = False

        if will_process:
            try:
                for user in will_process:
                    modifying_is_admin = await is_admin_or_superior(ctx.bot, user) or any(
                        [ur.id in support for ur in user.roles]
                    )
                    if modifying_is_admin:
                        failed.append(user)
                        continue
                    if user.id in self.ticket["added"]:
                        try:
                            await channel.set_permissions(
                                user, send_messages=False, read_messages=False
                            )
                        except discord.Forbidden:
                            failed_embed = discord.Embed(
                                title="Add/Remove Ticket Member Failed",
                                description=(
                                    "Failed to Add/Remove Members.  Please ensure I have "
                                    "Manage Permissions in that channel."
                                ),
                                color=0xFF0000,
                            )
                            # TODO: uncomment
                            # interaction.response.edit_message(embed=failed_embed, view=None)
                            await self.parent.original.edit(embed=failed_embed, view=None)
                            raise RuntimeError
                        else:
                            removed.append(user)
                            self.ticket["added"].remove(user.id)
                    else:
                        try:
                            await channel.set_permissions(
                                user, send_messages=True, read_messages=True
                            )
                        except discord.Forbidden:
                            failed_embed = discord.Embed(
                                title="Add/Remove Ticket Member Failed",
                                description=(
                                    "Failed to Add/Remove Members.  Please ensure I have "
                                    "Manage Permissions in that channel."
                                ),
                                color=0xFF0000,
                            )
                            # TODO: uncomment
                            # interaction.response.edit_message(embed=failed_embed, view=None)
                            await self.parent.original.edit(embed=failed_embed, view=None)
                            raise RuntimeError
                        else:
                            added.append(user)
                            self.ticket["added"].append(user.id)
            except RuntimeError:
                exit_early = True
            finally:
                # We put this in a finally so that we can add/remove in config no matter what
                # In case discord shits or something (which could certainly happen), we may
                # want to save members we have added/removed in config even if a later one
                # fails.
                async with cog.config.guild(ctx.guild).created() as created:
                    for index, i_ticket in enumerate(created[str(self.ticket["user"])]):
                        if i_ticket["channel"] == self.ticket["channel"]:
                            created[str(self.ticket["user"])][index]["added"] = self.ticket[
                                "added"
                            ]
                            break

        if not exit_early:
            results_embed = discord.Embed(
                title="Ticket Members Added/Removed",
                description="",
                color=await ctx.embed_color(),
            )
            if added:
                results_embed.description += (
                    humanize_list([member.mention for member in added])
                    + " were successfully added to the ticket.\n"
                )
            if removed:
                results_embed.description += (
                    humanize_list([member.mention for member in removed])
                    + " were successfully removed from the ticket.\n"
                )
            if failed:
                results_embed.description += humanize_list(
                    [getattr(member, "mention", member) for member in failed]
                ) + (
                    " could not be added/removed.  This may be because they are "
                    "an Administrator or I failed to find them.\n"
                )
            # TODO: uncomment
            # await interaction.response.edit_message(embed=results_embed, view=None)
            alert = Alert(embed=results_embed)
            await self.parent.original.edit(**alert.send())
            await alert.wait()

        self.timed_out = False
        self.repeat = True
        self.stop()

    @discord.ui.button(
        label="Lock Ticket", style=discord.ButtonStyle.danger, emoji="\N{LOCK}",
    )
    async def toggle_ticket_lock(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if self.ticket["locked"]:
            confirm = Confirmation(
                title="Unlock Ticket?",
                description="Are you sure you want to unlock this ticket?",
                color=await self.ctx.embed_color(),
            )
        else:
            confirm = Confirmation(
                title="Lock Ticket?",
                description="Are you sure you want to lock this ticket?",
                color=await self.ctx.embed_color(),
            )

        await interaction.response.edit_message(**confirm.send())
        result = await confirm.result()

        if result:
            if self.ticket["locked"]:
                await self.ctx.cog.unlock_ticket(self.ctx, self.ticket)
            else:
                await self.ctx.cog.lock_ticket(self.ctx, self.ticket)
        else:
            await interaction.response.send_message("Cancelled", ephemeral=True)

        self.timed_out = False
        self.repeat = True
        # self.parent.tickets[self.parent.page][self.parent.processing.counter - 1][
        #    "locked"
        # ] = not self.ticket["locked"]
        self.ticket["locked"] = not self.ticket["locked"]
        self.stop()

    @discord.ui.button(
        label="Archive/Close Ticket", style=discord.ButtonStyle.danger,
    )
    async def close_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        guild_settings = await self.ctx.cog.config.guild(self.ctx.guild).all()

        if guild_settings["archive"]["enabled"]:
            confirm = Confirmation(
                title="Archive Ticket?",
                description="Are you sure you want to archive this ticket?",
                color=await self.ctx.embed_color(),
            )
        else:
            confirm = Confirmation(
                title="Close Ticket?",
                description="Are you sure you want to close this ticket?",
                color=await self.ctx.embed_color(),
            )

        await interaction.response.edit_message(**confirm.send())
        result = await confirm.result()
        if result:
            author = self.ctx.guild.get_member(self.ticket["user"])
            channel = self.ctx.bot.get_channel(self.ticket["channel"])
            archive = self.ctx.bot.get_channel(guild_settings["archive"]["category"])
            added_users = [
                user for u in self.ticket["added"] if (user := self.ctx.guild.get_member(u))
            ]
            added_users.append(author)

            async with self.ctx.cog.config.guild(self.ctx.guild).created() as created:
                for index, i_ticket in enumerate(created[str(author.id)]):
                    if i_ticket["channel"] == self.ticket["channel"]:
                        del created[str(author.id)][index]
                        break

            await self.ctx.cog.report_close(
                ctx=self.ctx,
                ticket=self.ticket,
                author=author,
                guild_settings=guild_settings,
                reason="",
            )

            # This one can take a while, so we'll schedule this in a task
            self.ctx.bot.loop.create_task(
                self.ctx.cog.process_closed_ticket(
                    ctx=self.ctx,
                    guild_settings=guild_settings,
                    channel=channel,
                    archive=archive,
                    author=author,
                    added_users=added_users,
                )
            )
            self.timed_out = False
            self.stop()
        else:
            await interaction.response.send_message("Cancelled", ephemeral=True)
            self.timed_out = False
            self.repeat = True
            self.stop()

    @discord.ui.button(
        label="Return to Ticket Queue",
        style=discord.ButtonStyle.primary,
        emoji="\N{LEFTWARDS BLACK ARROW}",
        row=1,
    )
    async def return_to_queue(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.timed_out = False
        self.stop()

    async def on_timeout(self):
        await self.parent.original.edit(content="This message has expired.", view=None)
