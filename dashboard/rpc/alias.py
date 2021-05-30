from html import escape

import discord
from redbot.core.bot import Red
from redbot.core.commands import commands
from redbot.core.utils.chat_formatting import humanize_list

from .utils import permcheck, rpccheck


class DashboardRPC_AliasCC:
    def __init__(self, cog: commands.Cog):
        self.bot: Red = cog.bot
        self.cog: commands.Cog = cog

        # Initialize RPC handlers
        self.bot.register_rpc_handler(self.fetch_aliases)

    def unload(self):
        self.bot.unregister_rpc_handler(self.fetch_aliases)

    @rpccheck()
    @permcheck("Alias", ["aliascc"])
    async def fetch_aliases(self, guild: discord.Guild, member: discord.Member):
        aliascog = self.bot.get_cog("Alias")
        aliases = await aliascog._aliases.get_guild_aliases(guild)

        ida = {}
        for alias in aliases:
            if len(alias.command) > 50:
                command = alias.command[:47] + "..."
            else:
                command = alias.command
            if alias.command not in ida:
                ida[alias.command] = {"aliases": [], "shortened": escape(command)}
            ida[alias.command]["aliases"].append(f"{escape(alias.name)}")

        data = {}
        for command, aliases in ida.items():
            data[command] = {
                "humanized": humanize_list(
                    list(map(lambda x: f"<code>{x}</code>", aliases["aliases"]))
                ),
                "raw": aliases["aliases"],
                "shortened": aliases["shortened"],
            }
        return data
