from redbot.core.utils.chat_formatting import pagify
from redbot.core import Config, commands
from redbot.core.bot import Red
from datetime import datetime
from typing import Optional
import contextlib
import logging
import aiohttp
import asyncio
import discord


class OpenSea(commands.Cog):
    """Cog to interact with OpenSea and keep track of wallet events.

    This is a bounty cog, processed through the Red Cogboard.  Features
    that are implemented are not guaranteed and are up to discretion of
    the involved parties."""

    BASE = "https://api.opensea.io/api/v1"

    def __init__(self, bot):
        self.bot: Red = bot

        self.conf = Config.get_conf(self, identifier=473541068378341376)
        self.conf.register_global(contract_addresses={}, account_addresses={})

        # Mapping as follows:
        #   "contract_addresses": {
        #       "OPENSEA_CONTRACT_ADDRESS": {
        #           "subbed": ["DISCORD_CHANNEL_ID"],
        #           "last_event_id": 0,
        #       },
        #   },
        #   "account_addresses": {
        #       "OPENSEA_ACCOUNT_ADDRESS": [
        #           "subbed": ["DISCORD_CHANNEL_ID"],
        #           "last_event_id": 0,
        #       ],
        #   },

        self.task = asyncio.create_task(self.background_task())
        self.logger = logging.getLogger("red.3pt.cog.toxic.opensea")

    def cog_unload(self):
        self.task.cancel()

    async def background_task(self):
        await self.bot.wait_until_ready()
        while True:
            try:
                await self.fetch_updates()
            except Exception as e:
                self.logger.exception(e)
            await asyncio.sleep(60)

    async def fetch_updates(self):
        keys = await self.bot.get_shared_api_tokens("opensea")
        if (api_key := keys.get("api_key")) is None:
            return

        async with aiohttp.ClientSession() as session:
            initial_config = await self.conf.all()
            for address, stored in initial_config["contract_addresses"].items():
                if not stored["subbed"]:
                    continue
                json = {
                    "event_type": "successful",
                    "only_opensea": "false",
                    "asset_contract_address": address,
                }
                headers = {
                    "Content-Type": "application/json",
                    "X-API-KEY": api_key,
                }
                async with session.get(
                    OpenSea.BASE + "/events", params=json, headers=headers
                ) as req:
                    if req.status == 400:
                        async with self.conf.contract_addresses() as contract_addresses:
                            del contract_addresses[address]
                        continue
                    asset_events = await req.json()

                if len(asset_events["asset_events"]) == 0:
                    async with self.conf.contract_addresses() as contract_addresses:
                        del contract_addresses[address]
                    continue

                if asset_events["asset_events"][0]["id"] != stored["last_event_id"]:
                    to_publish = []
                    if stored["last_event_id"] != 0:
                        for event in asset_events["asset_events"]:
                            if event["id"] != stored["last_event_id"]:
                                to_publish.append(event)
                            else:
                                break
                    else:
                        to_publish.append(asset_events["asset_events"][0])

                    for update in to_publish:
                        remove_channels = await self.publish_update(stored["subbed"], update)
                        if remove_channels:
                            async with self.conf.contract_addresses() as contract_addresses:
                                for channel_id in remove_channels:
                                    contract_addresses[address]["subbed"].remove(channel_id)

                    async with self.conf.contract_addresses() as contract_addresses:
                        contract_addresses[address]["last_event_id"] = asset_events[
                            "asset_events"
                        ][0]["id"]

            for address, stored in initial_config["account_addresses"].items():
                if not stored["subbed"]:
                    continue
                json = {
                    "event_type": "successful",
                    "only_opensea": "false",
                    "account_address": address,
                }
                headers = {
                    "Content-Type": "application/json",
                    "X-API-KEY": api_key,
                }
                async with session.get(
                    OpenSea.BASE + "/events", params=json, headers=headers
                ) as req:
                    if req.status == 400:
                        async with self.conf.account_addresses() as account_addresses:
                            del account_addresses[address]
                        continue
                    asset_events = await req.json()

                if len(asset_events["asset_events"]) == 0:
                    async with self.conf.account_addresses() as account_addresses:
                        del account_addresses[address]
                    continue

                if asset_events["asset_events"][0]["id"] != stored["last_event_id"]:
                    to_publish = []
                    if stored["last_event_id"] != 0:
                        for event in asset_events["asset_events"]:
                            if event["id"] != stored["last_event_id"]:
                                to_publish.append(event)
                            else:
                                break
                    else:
                        to_publish.append(asset_events["asset_events"][0])

                    for update in to_publish:
                        remove_channels = await self.publish_update(stored["subbed"], update)
                        if remove_channels:
                            async with self.conf.account_addresses() as account_addresses:
                                for channel_id in remove_channels:
                                    account_addresses[address]["subbed"].remove(channel_id)

                    async with self.conf.account_addresses() as account_addresses:
                        account_addresses[address]["last_event_id"] = asset_events["asset_events"][
                            0
                        ]["id"]

    async def publish_update(self, subscribed, event):
        embed = discord.Embed(
            title=event["asset"]["name"],
            description=event["asset"]["description"],
            url=event["asset"]["permalink"],
            timestamp=datetime.fromisoformat(event["created_date"]),
        )
        embed.set_thumbnail(url=event["asset"]["collection"]["image_url"])
        embed.add_field(name="Name", value=event["asset"]["name"], inline=True)
        embed.add_field(
            name="Amount", value=str(int(event["total_price"]) / (10 ** 18)) + "Ξ", inline=True
        )

        if event["winner_account"]["user"] and event["winner_account"]["user"]["username"]:
            buyer = event["winner_account"]["user"]["username"]
        else:
            buyer = event["winner_account"]["address"]

        embed.add_field(name="Buyer", value=buyer, inline=False)

        if event["seller"]["user"] and event["seller"]["user"]["username"]:
            seller = event["seller"]["user"]["username"]
        else:
            seller = event["seller"]["address"]

        embed.add_field(name="Seller", value=seller, inline=False)

        embed.set_image(url=event["asset"]["image_url"])
        embed.set_footer(
            text="Sold on OpenSea", icon_url="https://opensea.io/static/images/logos/opensea.svg"
        )

        remove_channels = []

        for channel_id in subscribed:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                remove_channels.append(channel_id)
                continue

            color = await self.bot.get_embed_color(channel)
            embed.color = color

            with contextlib.suppress(discord.HTTPException):
                await channel.send(embed=embed)

        return remove_channels

    @commands.mod_or_permissions(manage_messages=True)
    @commands.group(aliases=["os"])
    async def opensea(self, ctx):
        """Receive events from OpenSea regarding assets."""
        pass

    @opensea.command(aliases=["addaccount"])
    async def addwallet(self, ctx, address: str, channel: Optional[discord.TextChannel]):
        """Add a wallet address to keep track of to a channel."""
        if channel is None:
            channel = ctx.channel

        keys = await self.bot.get_shared_api_tokens("opensea")
        if keys.get("api_key") is None:
            return await ctx.send(
                f"No API key is set.  Please set one with `{ctx.prefix}"
                "set api opensea api_key,YOUR_API_KEY_HERE`."
            )

        if not (
            channel.permissions_for(ctx.guild.me).send_messages
            and channel.permissions_for(ctx.guild.me).embed_links
        ):
            return await ctx.send(
                f"I require the Send Messages and Embed links permissions {channel.mention}."
            )

        async with self.conf.account_addresses() as account_addresses:
            if address in account_addresses:
                if channel.id in account_addresses[address]["subbed"]:
                    return await ctx.send(f"{channel.mention} is already subscribed to {address}.")
                account_addresses[address]["subbed"].append(channel.id)
            else:
                account_addresses[address] = {
                    "subbed": [channel.id],
                    "last_event_id": 0,
                }

        await ctx.send(
            f"Events from wallet address {address} will now be sent to {channel.mention}."
        )

    @opensea.command(aliases=["removeaccount"])
    async def removewallet(self, ctx, address: str, channel: Optional[discord.TextChannel]):
        """Remove a wallet address from a channel."""
        if channel is None:
            channel = ctx.channel

        async with self.conf.account_addresses() as account_addresses:
            if address not in account_addresses:
                return await ctx.send(f"{channel.mention} is not subscribed to {address}.")

            if channel.id not in account_addresses[address]["subbed"]:
                return await ctx.send(f"{channel.mention} is not subscribed to {address}.")

            account_addresses[address]["subbed"].remove(channel.id)

        await ctx.send(f"Successfully unsubscribed {channel.mention} from {address}.")

    @opensea.command(aliases=["addcontract"])
    async def addproject(self, ctx, address: str, channel: Optional[discord.TextChannel]):
        """Add a project/contract address to keep track of to a channel."""
        if channel is None:
            channel = ctx.channel

        keys = await self.bot.get_shared_api_tokens("opensea")
        if keys.get("api_key") is None:
            return await ctx.send(
                f"No API key is set.  Please set one with `{ctx.prefix}"
                "set api opensea api_key,YOUR_API_KEY_HERE`."
            )

        if not (
            channel.permissions_for(ctx.guild.me).send_messages
            and channel.permissions_for(ctx.guild.me).embed_links
        ):
            return await ctx.send(
                f"I require the Send Messages and Embed links permissions {channel.mention}."
            )

        async with self.conf.contract_addresses() as contract_addresses:
            if address in contract_addresses:
                if channel.id in contract_addresses[address]["subbed"]:
                    return await ctx.send(f"{channel.mention} is already subscribed to {address}.")
                contract_addresses[address]["subbed"].append(channel.id)
            else:
                contract_addresses[address] = {
                    "subbed": [channel.id],
                    "last_event_id": 0,
                }

        await ctx.send(
            f"Events from project address {address} will now be sent to {channel.mention}."
        )

    @opensea.command(aliases=["removecontract"])
    async def removeproject(self, ctx, address: str, channel: Optional[discord.TextChannel]):
        """Remove a project/contract address from a channel."""
        if channel is None:
            channel = ctx.channel

        async with self.conf.contract_addresses() as contract_addresses:
            if address not in contract_addresses:
                return await ctx.send(f"{channel.mention} is not subscribed to {address}.")

            if channel.id not in contract_addresses[address]["subbed"]:
                return await ctx.send(f"{channel.mention} is not subscribed to {address}.")

            contract_addresses[address]["subbed"].remove(channel.id)

        await ctx.send(f"Successfully unsubscribed {channel.mention} from {address}.")

    @opensea.command()
    async def listaddresses(self, ctx, channel: Optional[discord.TextChannel]):
        """List the addresses that a channel is subscribed to."""
        if channel is None:
            channel = ctx.channel

        wallets = []
        projects = []

        async with self.conf.contract_addresses() as contract_addresses:
            for address, stored in contract_addresses.items():
                if channel.id in stored["subbed"]:
                    projects.append(address)

        async with self.conf.account_addresses() as account_addresses:
            for address, stored in account_addresses.items():
                if channel.id in stored["subbed"]:
                    wallets.append(address)

        message = ""

        if wallets:
            message += (
                f"{channel.mention} is subscribed to the following wallet addresses:\n"
                f"{', '.join(wallets)}\n"
            )

        if projects:
            message += (
                f"{channel.mention} is subscribed to the following project addresses:\n"
                f"{', '.join(projects)}"
            )

        for page in pagify(message, delims=["\n", ","]):
            await ctx.send(page)

    @commands.is_owner()
    @opensea.command(hidden=True)
    async def forceupdate(self, ctx):
        """Force an update of all subscribed channels."""
        await self.fetch_updates()
        await ctx.send("Done.")
