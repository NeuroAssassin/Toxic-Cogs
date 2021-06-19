from typing import Optional
import discord


class Confirmation(discord.ui.View):
    def __init__(self, title: str, description: str, color: int):
        self.title: str = title
        self.description: str = description
        self.color: int = color

        self._result: Optional[bool] = None

        super().__init__(timeout=60.0)

    def send(self):
        embed: discord.Embed = discord.Embed(
            title=self.title, description=self.description, color=self.color
        )
        return {"embed": embed, "view": self}

    async def result(self):
        await self.wait()
        return self._result

    @discord.ui.button(label="Yes, continue", style=discord.ButtonStyle.success)
    async def response_continue(self, button: discord.ui.Button, interaction: discord.Interaction):
        self._result = True
        self.stop()

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.danger)
    async def response_cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self._result = False
        self.stop()
