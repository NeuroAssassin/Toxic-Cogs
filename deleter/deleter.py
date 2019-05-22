from redbot.core.utils.chat_formatting import humanize_list
from redbot.core import commands, checks, Config
import time
import discord
import asyncio
from copy import deepcopy as dc

class Deleter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=473541068378341376)
        default_channel = {
            "wait": 0,
            "messages": {}
        }
        self.conf.register_channel(**default_channel)
        self.task = self.bot.loop.create_task(self.background_task())

    def cog_unload(self):
        self.task.cancel()

    async def background_task(self):
        await self.bot.wait_until_ready()
        while True:
            cs = await self.conf.all_channels()
            for channel, data in cs.items():
                if int(data["wait"]) == 0:
                    continue
                c = self.bot.get_channel(int(channel))
                old = dc(data)
                ms = dc(data["messages"])
                for message, wait in ms.items():
                    if int(wait) <= time.time():
                        try:
                            m = await c.fetch_message(int(message))
                            await m.delete()
                        except (discord.NotFound, discord.Forbidden):
                            pass
                        del data["messages"][str(message)]
                if old != data:
                    await self.conf.channel(c).messages.set(data["messages"])
            await asyncio.sleep(5)

    @commands.Cog.listener()
    async def on_message(self, message):
        c = await self.conf.channel(message.channel).all()
        if int(c["wait"]) == 0:
            return
        c["messages"][str(message.id)] = time.time() + int(c["wait"])
        await self.conf.channel(message.channel).messages.set(c["messages"])

    @commands.group()
    @checks.mod_or_permissions(manage_messages=True)
    async def deleter(self, ctx):
        """Group command for commands dealing with auto-timed deletion"""
        pass

    @deleter.command()
    async def channel(self, ctx, channel: discord.TextChannel, wait: int):
        """Set the amount of time after a message is sent it is supposed to be deleted.

        There may be about an approximate 5 second difference between the wait and the actual time it is deleted.
        
        Wait times must be greater than or equal to 5 seconds, or 0 to disable auto-timed deletion."""
        if wait < 5 and wait != 0:
            return await ctx.send("Wait times must be greater than or equal to 5 seconds.")
        if not channel.permissions_for(ctx.guild.me).manage_messages:
            return await ctx.send("I do not have permission to delete messages in that channel.")
        if not channel.permissions_for(ctx.author).manage_messages:
            return await ctx.send("You do not have permission to delete messages in that channel.")
        await self.conf.channel(channel).wait.set(str(wait))
        if wait:
            await ctx.send(f"Messages in {channel.mention} will now be deleted after {wait} seconds.")
        else:
            await ctx.send("Messages will not be auto-deleted after a specific amount of time.")

    @deleter.command()
    async def remove(self, ctx, channel: discord.TextChannel, *messages: str):
        """Remove messages from the auto-timed deletion.  Helpful for when announcements that you want to stay in the channel."""
        failed = []
        success = []
        msgs = await self.conf.channel(channel).messages()
        for m in messages:
            if not m in msgs:
                failed.append(m)
                continue
            del msgs[m]
            success.append(m)
        if not failed:
            failed = [None]
        if not success:
            success = [None]
        await self.conf.channel(channel).messages.set(msgs)
        await ctx.send(f"Messages successfully removed: {humanize_list(success)}\nMessages that failed to be removed: {humanize_list(failed)}")

    @deleter.command()
    @checks.admin()
    async def wipe(self, ctx, channel: discord.TextChannel = None):
        """Removes all messages in the specified channel from the auto-timed deleter.

        Leave blank to do it for the current channel"""
        if not channel:
            channel = ctx.channel
        await self.conf.channel(channel).messages.set({})
        await ctx.tick()