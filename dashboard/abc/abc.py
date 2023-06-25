from abc import ABC, abstractmethod

from redbot.core import Config, commands
from redbot.core.bot import Red


class MixinMeta(ABC):
    """Base class for well behaved type hint detection with composite class.
    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    def __init__(self, *_args):
        self.config: Config
        self.bot: Red

    @commands.group(name="dashboard")
    async def dashboard(self, ctx: commands.Context):
        """Group command for controlling the web dashboard for Red."""
        pass
