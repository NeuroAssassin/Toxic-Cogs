from abc import ABC

from redbot.core import Config
from redbot.core.bot import Red


class MixinMeta(ABC):
    """Base class for well behaved type hint detection with composite class.
    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    def __init__(self, *_args):
        self.config: Config
        self.bot: Red

    async def embed_requested(self, channel):
        # Copy of ctx.embed_requested, but with the context taken out
        if not channel.permissions_for(channel.guild.me).embed_links:
            return False

        channel_setting = await self.bot._config.channel(channel).embeds()
        if channel_setting is not None:
            return channel_setting

        guild_setting = await self.bot._config.guild(channel.guild).embeds()
        if guild_setting is not None:
            return guild_setting

        return await self.bot._config.embeds()
