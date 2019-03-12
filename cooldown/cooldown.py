from redbot.core import commands, checks, Config
from discord.ext import commands as dc
import asyncio
import time
import traceback

class CooldownFailure(dc.CommandError):
    pass

class Cooldown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=473541068378341376)
        default_global = {'data': []}
        self.conf.register_global(**default_global)
        self.task = self.bot.loop.create_task(self.initialize())

    def __unload(self):
        self.task.cancel()

    async def initialize(self):
        try:
            await self.bot.wait_until_ready()
            data = await self.conf.data()
            for entry in data:
                cmd = self.bot.get_command(entry[0])
                if cmd:
                    switch = {
                        "user": dc.BucketType.user,
                        "channel": dc.BucketType.channel,
                        "guild": dc.BucketType.guild,
                        "global": dc.BucketType.default
                    }
                    bctype = switch[entry[3]]
                    commands.cooldown(entry[1], entry[2], bctype)(cmd)
                else:
                    print("no exist")
        except Exception as e:
            print(e)


    @commands.group()
    async def cooldown(self, ctx):
        """Group command for working with cooldowns for commands.

        Do note however that this will NOT change any cooldowns set in cog's code"""
        pass

    @checks.is_owner()
    @cooldown.command(alises=["update", "change"])
    async def add(self, ctx, rate: int, per, btype, *, command):
        """Sets a cooldown for a command, allowing a certain amount of times in a certain amount of time for a certain type.

        Example: `[p]cooldown add 1 5s user ping`

        The above example will limit a user to using the `ping` command every 5 seconds.

        Example 2: `[p]cooldown add 5 10m guild ban`

        The above example (number 2) will limit people in a guild to using the `ban` command to 5 times every 10 minutes.

        Time Types:
        -   S   =>  Seconds
        -   M   =>  Minutes
        -   H   =>  Hours
        -   D   =>  Days

        Bucket Types:
        -   User
        -   Channel
        -   Guild
        -   Global (owner only)

        Arguments:
        -   Rate:      how many times
        -   Per:       during how long
        -   Type:      for what type
        -   Command:   for what command.  Do not use a prefix, and does not work with aliases.  Please pass the actual command for the alias if you wish"""
        ttype = None
        per = per.lower()
        if per.endswith("s"):
            ttype = "seconds"
        elif per.endswith("m"):
            ttype = "minutes"
        elif per.endswith("h"):
            ttype = "hours"
        elif per.endswith("d"):
            ttype = "days"
        if not ttype:
            return await ctx.send("Invalid time unit.  Please use S, M, H or D.")
        np = per[:(len(per)-1)]
        if not np.isdigit():
            return await ctx.send("Invalid amount of time.  There is a non-number in your per argument, not including the time type.")
        np = int(np)
        if ttype == "minutes":
            np *= 60
        elif ttype == "hours":
            np *= 3600
        elif ttype == "days":
            np *= 86400
        btype = btype.lower()
        if not btype in ["user", "channel", "guild", "global"]:
            return await ctx.send("Invalid bucket type.")
        if (btype == "global") and (not (self.bot.is_owner(ctx.author))):
            return await ctx.send("Only the bot owner is allowed to set a bucket type to global.")
        cmd = self.bot.get_command(command)
        if cmd == None:
            return await ctx.send("Invalid command argument.")
        if (cmd.requires.privilege_level._name_ == "BOT_OWNER") and (not (self.bot.is_owner(ctx.author))):
            return await ctx.send("You are not allowed to put cooldowns on an owner only command.")
        if isinstance(cmd, commands.commands.Group):
            await ctx.send("You are about to set a group command for a cooldown.  This will only work when they are invoking it plainly, without any other subcommands.")

        if ttype == "minutes":
            np *= 60
        elif ttype == "hours":
            np *= 3600
        elif ttype == "days":
            np *= 86400

        def check(m):
            return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id) and (m.content[0].lower() in ['y', 'n'])

        message = (
            "You are about to add a cooldown for a command using this cog.  "
            "Are you sure you wish to set this cooldown?  Respond with 'y' or 'n' to this message."
        )

        await ctx.send(message)
        try:
            m = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long to respond.")
        if m.content.lower().startswith("y"):
            switch = {
                "user": dc.BucketType.user,
                "channel": dc.BucketType.channel,
                "guild": dc.BucketType.guild,
                "global": dc.BucketType.default
            }
            bctype = switch[btype]
            commands.cooldown(rate, np, bctype)(cmd)
        else:
            return await ctx.send("Not establishing command cooldown.")
        data = [command, rate, np, btype]
        all_data = await self.conf.data()
        changed = False
        for entry in all_data:
            if (entry[0] == data[0]) and (entry[3] == data[3]):
                entry = data
                changed = True
        if not changed:
            all_data.append(data)
        await self.conf.data.set(all_data)

        await ctx.send("Your cooldown has been established")

    @checks.is_owner()
    @cooldown.command()
    async def remove(self, ctx, btype, *, command):
        """Removes the cooldown from a command, under a specific bucket.

        The cooldown can be one set from this cog or from inside the cog's code.

        Please do note however: some commands are meant to have cooldowns.  They may prevent something malicious from happening, or maybe your device from breaking or from being used too much.  I (Neuro Assassin <@473541068378341376>) take no responsibility for any complications that may result because of this.  Use at your own risk.

        Bucket Types:
        -   User
        -   Channel
        -   Guild
        -   Global (owner only)
        
        Note: Does not actually remove the command cooldown (undocumented), so instead it allows for the command to be run 100000 times every 1 second until the next boot up, where it will not be added."""
        cmd = self.bot.get_command(command)
        if cmd == None:
            return await ctx.send("Invalid command argument.")
        if (cmd.requires.privilege_level._name_ == "BOT_OWNER") and (not (self.bot.is_owner(ctx.author))):
            return await ctx.send("You are not allowed to put cooldowns on an owner only command.")
        btype = btype.lower()
        if not btype in ["user", "channel", "guild", "global"]:
            return await ctx.send("Invalid bucket type.")
        if (btype == "global") and (not (self.bot.is_owner(ctx.author))):
            return await ctx.send("Only the bot owner is allowed to set a bucket type to global.")
        def check(m):
            return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id) and (m.content[0].lower() in ['y', 'n'])

        message = (
            "You are about to remove a cooldown for a command.  "
            "Are you sure you wish to remove it?  Respond with 'y' or 'n' to this message."
        )

        await ctx.send(message)
        try:
            m = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long to respond.")
        if m.content.lower().startswith("y"):
            switch = {
                "user": dc.BucketType.user,
                "channel": dc.BucketType.channel,
                "guild": dc.BucketType.guild,
                "global": dc.BucketType.default
            }
            bctype = switch[btype]
            commands.cooldown(10000, 1, bctype)(cmd)
        else:
            return await ctx.send("Not removing command cooldown.")
        data = await self.conf.data()
        for entry in data:
            if (entry[0] == command) and (entry[3] == btype):
                data.remove(entry)
        await self.conf.data.set(data)

        await ctx.send("Your cooldown has been removed.")