from redbot.core import commands


class DBMixin:
    """ This is mostly here to easily mess with things... """

    @commands.group(name="dashboard")
    async def dashboard(self, ctx: commands.Context):
        """Group command for controlling the web dashboard for Red."""
        pass