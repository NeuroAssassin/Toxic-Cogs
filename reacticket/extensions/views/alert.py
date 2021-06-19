from typing import Optional
import discord


class Alert(discord.ui.View):
    def __init__(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[int] = None,
        embed: Optional[discord.Embed] = None,
    ):
        if not embed and not ((title or description) and color):
            raise ValueError(
                "Either embed, or color with a title or description must be provided."
            )

        self.title: Optional[str] = title
        self.description: Optional[str] = description
        self.color: Optional[int] = color

        self.embed: discord.Embed = embed or discord.Embed(
            title=self.title, description=self.description, color=self.color
        )

        super().__init__(timeout=10.0)

    def send(self):
        return {"embed": self.embed, "view": self}

    @discord.ui.button(label="Acknowledge", style=discord.ButtonStyle.success)
    async def response_continue(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.stop()
