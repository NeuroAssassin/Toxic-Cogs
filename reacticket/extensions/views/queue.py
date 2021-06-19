from redbot.core.commands.context import Context
from typing import List, Optional
from datetime import datetime
import discord

from reacticket.extensions.views.ticket import Ticket

SPACE = " \N{ZERO WIDTH SPACE}"


class QueueTicketButton(discord.ui.Button["Queue"]):
    def __init__(self, counter):
        self.counter = counter

        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=f"#{counter}",
            emoji="\N{ADMISSION TICKETS}",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = self.view
        view.processing = self

        ticket = view.tickets[view.page][self.counter - 1]
        tview = Ticket(view.ctx, ticket, view)

        await tview.build_embed()
        await view.original.edit(embed=tview.embed, view=tview)

        await tview.wait()
        if not tview.timed_out and not tview.repeat:
            updated_tickets = await view.ctx.cog.config.guild(view.ctx.guild).created()
            try:
                tickets = view.ctx.cog.sort_tickets(updated_tickets)
            except ValueError:
                embed = discord.Embed(
                    title="Open tickets",
                    description="No tickets are currently open.",
                    color=await view.ctx.embed_color(),
                )
                await view.original.edit(embed=embed, view=None)
                view.stop()  # Just to make sure
                return

            new_queue = Queue(view.ctx, tickets)
            new_queue.page = view.page
            new_queue.refresh_ticket_row()
            await new_queue.build_embed()

            new_queue.set_message(view.original)
            await view.original.edit(embed=new_queue.embed, view=new_queue)
        elif not tview.timed_out:
            await self.callback(interaction)

        view.processing = None


class Queue(discord.ui.View):
    def __init__(self, ctx: Context, tickets: List):
        self.ctx: Context = ctx
        self.tickets: List = tickets

        self.page: int = 0
        self.embed: Optional[discord.Embed] = None
        self.original: Optional[discord.Message] = None
        self.processing: Optional[discord.ui.Button] = None

        super().__init__()

        self.refresh_ticket_row()

    def set_message(self, message: discord.Message):
        self.original = message

    def refresh_ticket_row(self):
        if len(self.tickets) == 1:
            self.clear_items()
        else:
            for child in self.children.copy():
                if child.row == 0:
                    self.remove_item(child)

        for ticket_num in range(1, len(self.tickets[self.page]) + 1):
            self.add_item(QueueTicketButton(ticket_num))

    async def build_embed(self):
        self.embed = discord.Embed(
            title="Open tickets", description="", color=await self.ctx.embed_color()
        )

        counter = 1
        for ticket in self.tickets[self.page]:
            user = getattr(self.ctx.guild.get_member(ticket["user"]), "mention", "Removed user")
            timestamp = datetime.fromtimestamp(ticket["opened"]).strftime("%B %d, %Y at %H:%M UTC")
            self.embed.description += f"**{counter}.** Ticket created by {user} on {timestamp}\n"
            counter += 1

    @discord.ui.button(
        label=SPACE * 6,
        style=discord.ButtonStyle.secondary,
        emoji="\N{LEFTWARDS BLACK ARROW}",
        row=1,
    )
    async def page_left(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.page == 0:
            self.page = len(self.tickets) - 1
        else:
            self.page -= 1

        self.refresh_ticket_row()
        await self.build_embed()
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label=SPACE * 14, style=discord.ButtonStyle.secondary, disabled=True, row=1)
    async def first_blank(self, *args, **kwargs):
        pass

    @discord.ui.button(label=SPACE * 14, style=discord.ButtonStyle.secondary, disabled=True, row=1)
    async def second_blank(self, *args, **kwargs):
        pass

    @discord.ui.button(label=SPACE * 14, style=discord.ButtonStyle.secondary, disabled=True, row=1)
    async def third_blank(self, *args, **kwargs):
        pass

    @discord.ui.button(
        label=SPACE * 6,
        style=discord.ButtonStyle.secondary,
        emoji="\N{BLACK RIGHTWARDS ARROW}",
        row=1,
    )
    async def page_right(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.page == len(self.tickets) - 1:
            self.page = 0
        else:
            self.page += 1

        self.refresh_ticket_row()
        await self.build_embed()
        await interaction.response.edit_message(embed=self.embed, view=self)

    async def on_timeout(self):
        if not self.processing:
            await self.original.edit(content="This message has expired.", view=None)
