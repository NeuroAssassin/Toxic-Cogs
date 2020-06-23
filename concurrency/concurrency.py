from redbot.core import commands, checks, Config
from discord.ext import commands as dc
import asyncio
import time
import traceback


async def check(ctx):  # For special people
    return ctx.author.id in [332980470650372096, 473541068378341376, 376564057517457408]


class Concurrency(commands.Cog):
    """Add or remove concurrencies from/to commands

    WARNING: This cog is in developmental status and not really tested; there is a reason why it is hidden.  It is only for special use cases."""

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=473541068378341376)
        default_global = {"data": []}
        self.conf.register_global(**default_global)
        self.task = self.bot.loop.create_task(self.initialize())

    def cog_unload(self):
        self.__unload()

    def __unload(self):
        self.task.cancel()

    async def initialize(self):
        await self.bot.wait_until_ready()
        data = await self.conf.data()
        for entry in data:
            cmd = self.bot.get_command(entry[0])
            if cmd:
                switch = {
                    "user": dc.BucketType.user,
                    "channel": dc.BucketType.channel,
                    "guild": dc.BucketType.guild,
                    "global": dc.BucketType.default,
                }
                commands.max_concurrency(entry[1], switch[entry[2]], wait=False)(cmd)

    @commands.group(hidden=True)
    async def concurrency(self, ctx):
        """Group command for working with concurrencies for commands."""
        pass

    @checks.is_owner()
    @concurrency.command(alises=["update", "change", "edit"])
    async def add(self, ctx, rate: int, btype, *, command):
        """Don't use this if you don't know what you're doing.
        
        First argument is amount of times it can be running at once, second is what bucket the concurrecy is based on, last one is command"""
        btype = btype.lower()
        if not btype in ["user", "channel", "guild", "global"]:
            return await ctx.send("Invalid bucket type.")
        cmd = self.bot.get_command(command)
        if cmd == None or not str(cmd) == command:
            return await ctx.send("Invalid command argument.")

        switch = {
            "user": dc.BucketType.user,
            "channel": dc.BucketType.channel,
            "guild": dc.BucketType.guild,
            "global": dc.BucketType.default,
        }
        commands.max_concurrency(rate, switch[btype], wait=False)(cmd)
        all_data = await self.conf.data()
        data = [command, rate, btype]
        changed = False
        for position, entry in enumerate(all_data):
            if entry[0] == data[0]:
                all_data[position] = data
                changed = True
                break
        if not changed:
            all_data.append(data)
        await self.conf.data.set(all_data)

        await ctx.send("Your concurrency rule has been established")

    @checks.is_owner()
    @concurrency.command()
    async def remove(self, ctx, *, command):
        """Removes the concurrency rule set in the cog.  Reload the affected cog for the change to take effect"""
        cmd = self.bot.get_command(command)
        if cmd == None or not str(cmd) == command:
            return await ctx.send("Invalid command argument.")

        data = await self.conf.data()
        if not command in [item[0] for item in data]:
            return await ctx.send("This command does not have any concurrency rule.")

        for entry in data:
            if entry[0] == command:
                data.remove(entry)
                break

        await self.conf.data.set(data)

        await ctx.send(
            "Your concurrency rule has been removed.  Reload the affected cog for the change to take effect."
        )

    @commands.check(check)
    @concurrency.command()
    async def test(self, ctx):
        await asyncio.sleep(20)
        await ctx.tick()

    @commands.check(check)
    @concurrency.command()
    async def refresh(self, ctx):
        """Refresh concurrencies, in case something gets stuck"""
        await self.initialize()
        await ctx.tick()
