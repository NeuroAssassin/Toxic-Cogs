from collections import defaultdict

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, humanize_list, inline
from abc import ABC

# ABC Mixins
from dashboard.abc.abc import MixinMeta
from dashboard.abc.mixin import DBMixin, dashboard

# Command Mixins
from dashboard.abc.roles import DashboardRolesMixin
from dashboard.abc.webserver import DashboardWebserverMixin
from dashboard.abc.settings import DashboardSettingsMixin

# RPC Mixins
from dashboard.baserpc import HUMANIZED_PERMISSIONS, DashboardRPC
from dashboard.menus import ClientList, ClientMenu

THEME_COLORS = ["red", "primary", "blue", "green", "greener", "yellow"]


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """This allows the metaclass used for proper type detection to coexist with discord.py's
    metaclass."""


# Thanks to Flare for showing how to use group commands across multiple files.  If this breaks, its his fault
class Dashboard(
    DashboardRolesMixin,
    DashboardWebserverMixin,
    DashboardSettingsMixin,
    DBMixin,
    commands.Cog,
    metaclass=CompositeMetaClass,
):

    __version__ = "0.1.7a"

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=473541068378341376)
        self.config.register_global(
            secret="[Not set]",
            redirect="http://127.0.0.1:42356/callback",
            clientid=0,
            blacklisted=[],
            disallowedperms=[],
            support="",
            defaultcolor="red",
            meta={"title": "", "icon": "", "description": "", "color": ""},
        )
        self.config.register_guild(roles=[])
        self.configcache = defaultdict(self.cache_defaults)

        self.rpc = DashboardRPC(self)

    def cog_unload(self):
        self.configcache.clear()
        self.rpc.unload()

    def cache_defaults(self):
        return {"roles": []}

    async def initialize(self):
        config = await self.config.all_guilds()
        for k, v in config.items():
            self.configcache[k] = v
