from redbot.core import commands, Config, checks
import discord
import datetime


class PayRespects(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=473541068378341376)
        self.conf.register_guild(postchannel=0, required=3, cache={}, blacklist=[])

    async def on_raw_reaction_remove(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.get_message(payload.message_id)
        guild = self.bot.get_guild(payload.guild_id)
        blacklisted = await self.conf.guild(guild).blacklist()
        if str(channel.id) in blacklisted:
            return
        if str(payload.emoji) != "\N{REGIONAL INDICATOR SYMBOL LETTER F}":
            return
        count = 0
        for reaction in message.reactions:
            if str(reaction) == "\N{REGIONAL INDICATOR SYMBOL LETTER F}":
                async for user in reaction.users():
                    if user.id != message.author.id and not user.bot:
                        count += 1
        messages = await self.conf.guild(guild).cache()
        if str(message.id) in messages:
            board_channel = self.bot.get_channel(await self.conf.guild(guild).postchannel())
            if board_channel:
                board_message = await board_channel.get_message(int(messages[str(message.id)]))
                if board_message:
                    required = await self.conf.guild(guild).required()
                    if count < required:
                        await board_message.delete()
                        del messages[str(message.id)]
                        return await self.conf.guild(guild).cache.set(messages)
                    previous_timestamp = board_message.embeds[0].timestamp
                    embed = discord.Embed(
                        description=message.content, color=0x0000FF, timestamp=previous_timestamp
                    )
                    embed.set_author(
                        name=message.author.display_name, icon_url=message.author.avatar_url
                    )
                    embed.add_field(name="Jump", value=f"[Click here]({message.jump_url})")
                    await board_message.edit(
                        content=f"\N{REGIONAL INDICATOR SYMBOL LETTER F} {channel.mention} ID: {message.id};  Respects paid: {count}",
                        embed=embed,
                    )

    async def on_raw_reaction_add(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.get_message(payload.message_id)
        guild = self.bot.get_guild(payload.guild_id)
        blacklisted = await self.conf.guild(guild).blacklist()
        if str(channel.id) in blacklisted:
            return
        if str(payload.emoji) != "\N{REGIONAL INDICATOR SYMBOL LETTER F}":
            return
        count = 0
        for reaction in message.reactions:
            if str(reaction) == "\N{REGIONAL INDICATOR SYMBOL LETTER F}":
                async for user in reaction.users():
                    if user.id != message.author.id and not user.bot:
                        count += 1
        messages = await self.conf.guild(guild).cache()
        if not str(message.id) in messages:
            required = await self.conf.guild(guild).required()
            if int(required) <= count:
                sending_channel = self.bot.get_channel(await self.conf.guild(guild).postchannel())
                if sending_channel:
                    try:
                        embed = discord.Embed(
                            description=message.content,
                            color=0x0000FF,
                            timestamp=datetime.datetime.utcnow(),
                        )
                        embed.set_author(
                            name=message.author.display_name, icon_url=message.author.avatar_url
                        )
                        embed.add_field(name="Jump", value=f"[Click here]({message.jump_url})")
                        m = await sending_channel.send(
                            f"\N{REGIONAL INDICATOR SYMBOL LETTER F} {channel.mention} ID: {message.id};  Respects paid: {count}",
                            embed=embed,
                        )
                        messages[str(message.id)] = str(m.id)
                        await self.conf.guild(guild).cache.set(messages)
                    except:
                        pass
            else:
                # Doesn't have enough emojis yet
                pass
        else:
            board_channel = self.bot.get_channel(await self.conf.guild(guild).postchannel())
            if board_channel:
                board_message = await board_channel.get_message(int(messages[str(message.id)]))
                if board_message:
                    previous_timestamp = board_message.embeds[0].timestamp
                    embed = discord.Embed(
                        description=message.content, color=0x0000FF, timestamp=previous_timestamp
                    )
                    embed.set_author(
                        name=message.author.display_name, icon_url=message.author.avatar_url
                    )
                    embed.add_field(name="Jump", value=f"[Click here]({message.jump_url})")
                    await board_message.edit(
                        content=f"\N{REGIONAL INDICATOR SYMBOL LETTER F} {channel.mention} ID: {message.id};  Respects paid: {count}",
                        embed=embed,
                    )

    @checks.admin()
    @commands.group()
    async def fboard(self, ctx):
        """Pay respects"""
        pass

    @fboard.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set the channel for respects to be paid"""
        await self.conf.guild(ctx.guild).postchannel.set(channel.id)
        await ctx.tick()

    @fboard.command()
    async def required(self, ctx, amount: int):
        """Set how many respects must be paid to be broadcasted"""
        await self.conf.guild(ctx.guild).required.set(amount)
        await ctx.tick()

    @fboard.command()
    async def blacklist(self, ctx, channel: discord.TextChannel):
        """Blacklist a channel to or from the F-board"""
        async with self.conf.guild(ctx.guild).blacklist() as blacklist:
            if str(channel.id) in blacklist:
                blacklist.remove(str(channel.id))
                msg = "The channel has been removed from the blacklist."
            else:
                blacklist.append(str(channel.id))
                msg = "The channel has been added to the blacklist."
        await ctx.send(msg)