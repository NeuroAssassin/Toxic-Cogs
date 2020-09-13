import asyncio
import time
import traceback
from typing import Optional

from discord.ext import commands as dc
from redbot.core import Config, checks, commands

from .converters import GlobalCooldownArgs


class CooldownCogCooldown:
    def __init__(
        self,
        rate: int,
        per: float,
        bucket: commands.BucketType,
        guild_id: Optional[int],
        elements,
    ):
        self.guild = guild_id
        self.elements = elements
        self.mapping = commands.CooldownMapping.from_cooldown(rate, per, bucket)

    def __call__(self, ctx: commands.Context):
        if not ctx.bot.get_cog("Cooldown"):
            return True
        key = self.mapping._bucket_key(ctx.message)
        if self.guild and self.guild != ctx.guild.id:
            return True  # The cooldown is not global, and it doesn't apply to this server
        if key in self.elements:
            bucket = self.mapping.get_bucket(ctx.message)
        else:
            return True
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(bucket, retry_after)
        # Cooldown is overwritten, so lets reset it
        ctx.command.reset_cooldown(ctx)
        return True


class Cooldown(commands.Cog):
    """Add or remove cooldowns from/to commands

    WARNING: Some cooldowns are meant to be in place, meaning that they should not be removed.
    Any contributors to this cog are not at fault if it is used improperly, and is instead at
    the fault of the person running the command.  By installing this cog, you agree to these terms."""

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=473541068378341376)

        default_global = {"data": [], "new_data": []}
        self.conf.register_global(**default_global)

        default_guild = {"data": []}
        self.conf.register_guild(**default_guild)

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
                commands.cooldown(entry[1], entry[2], switch[entry[3]])(cmd)

    @checks.guildowner()
    @commands.group()
    async def devcooldown(self, ctx):
        """Group command for working with cooldowns for commands."""
        pass

    @checks.is_owner()
    @devcooldown.group(name="global")
    async def devcooldown_global(self, ctx):
        """Create/remove a global cooldown"""

    @devcooldown_global.command(name="add")
    async def global_add(self, ctx, *, args: GlobalCooldownArgs):
        """Blah blah blah"""
        commands.check(
            CooldownCogCooldown(
                args["rate"], args["per"], args["bucket"], args["guild_id"], args["elements"]
            )
        )(self.bot.get_command(args["command"]))
        await ctx.tick()

    @checks.is_owner()
    @commands.group()
    async def cooldown(self, ctx):
        """Group command for working with cooldowns for commands."""
        pass

    @cooldown.command(alises=["update", "change", "edit"])
    async def add(self, ctx, rate: int, per, btype, *, command):
        """Sets a cooldown for a command, allowing a certain amount of times in a certain amount of time for a certain type.  If a cooldown already exists for the specified command, then it will be overwritten and edited.

        The command argument does not require quotes, as it consumes the rest in order to make cooldowns for subcommands easier.

        Example: `[p]cooldown add 1 5s user ping`

        The above example will limit a user to using the `ping` command every 5 seconds.

        Example 2: `[p]cooldown add 5 10m guild alias add`

        The above example (number 2) will limit people in a guild to using the `alias add` command to 5 times every 10 minutes.

        Time Types:
        -   S   =>  Seconds
        -   M   =>  Minutes
        -   H   =>  Hours
        -   D   =>  Days

        Bucket Types:
        -   User
        -   Channel
        -   Guild
        -   Global

        Arguments:
        -   Rate:      how many times
        -   Per:       during how long
        -   Type:      for what type
        -   Command:   for what command.  Do not use a prefix, and does not work with aliases.  Please pass the actual command for the alias if you wish."""
        ttype = None
        per = per.lower()
        np = per[:-1]
        if not np.isdigit():
            return await ctx.send(
                "Invalid amount of time.  There is a non-number in your `per` argument, not including the time type."
            )
        if rate < 1:
            return await ctx.send("The rate argument must be at least 1 or higher.")
        np = int(np)
        if per.endswith("s"):
            ttype = "seconds"
        elif per.endswith("m"):
            ttype = "minutes"
            np *= 60
        elif per.endswith("h"):
            ttype = "hours"
            np *= 3600
        elif per.endswith("d"):
            ttype = "days"
            np *= 86400
        if not ttype:
            return await ctx.send("Invalid time unit.  Please use S, M, H or D.")
        btype = btype.lower()
        if not btype in ["user", "channel", "guild", "global"]:
            return await ctx.send("Invalid bucket type.")
        cmd = self.bot.get_command(command)
        if cmd == None or not str(cmd) == command:
            return await ctx.send("Invalid command argument.")

        def check(m):
            return (
                (m.author.id == ctx.author.id)
                and (m.channel.id == ctx.channel.id)
                and (m.content[0].lower() in ["y", "n"])
            )

        cooldowns = cmd._buckets._cooldown
        all_data = await self.conf.data()
        if cooldowns:
            if not command in [item[0] for item in all_data]:
                extra = "\nThis command also had an original cooldown.  Cooldowns are typically on commands for certain reasons, and so editing it is not recommended.  Proceed at your own risk."
            else:
                extra = "\nThis command already had a cooldown from this cog, so its current cooldown will be edited to the new one."
        else:
            extra = ""

        await ctx.send(
            (
                "You are about to add a cooldown for a command using this cog.  "
                "Are you sure you wish to set this cooldown?  Respond with 'y' or 'n' to this message."
                f"{extra}"
            )
        )
        try:
            m = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long to respond.")
        if m.content.lower().startswith("y"):
            switch = {
                "user": dc.BucketType.user,
                "channel": dc.BucketType.channel,
                "guild": dc.BucketType.guild,
                "global": dc.BucketType.default,
            }
            commands.cooldown(rate, np, switch[btype])(cmd)
        else:
            return await ctx.send("Not establishing command cooldown.")
        data = [command, rate, np, btype]
        changed = False
        for position, entry in enumerate(all_data):
            if entry[0] == data[0]:
                all_data[position] = data
                changed = True
                break
        if not changed:
            all_data.append(data)
        await self.conf.data.set(all_data)

        await ctx.send("Your cooldown has been established")

    @cooldown.command()
    async def remove(self, ctx, *, command):
        """Removes the cooldown from a command.

        The cooldown can be one set from this cog or from inside the cog's code.

        The command argument does not require quotes, as it consumes the rest in order to make cooldowns for subcommands easier.

        Please do note however: some commands are meant to have cooldowns.  They may prevent something malicious from happening, or maybe your device from breaking or from being used too much.  I (Neuro Assassin <@473541068378341376>) or any other contributor to this cog take no responsibility for any complications that may result because of this.  Use at your own risk.

        Note: Does not actually remove the command cooldown (undocumented), so instead it allows for the command to be run 100000 times every 1 second until the next boot up, where it will not be added (unless you are removing a cooldown from outside of this cog, then it will be kept after restart)."""
        cmd = self.bot.get_command(command)
        if cmd == None or not str(cmd) == command:
            return await ctx.send("Invalid command argument.")

        cooldowns = cmd._buckets._cooldown
        if not cooldowns:
            return await ctx.send("This command does not have any cooldown.")

        data = await self.conf.data()
        if not command in [item[0] for item in data]:
            fromcog = False
            extra = "\nThis command also had an original cooldown.  Cooldowns are typically on commands for certain reasons, and so removing it is not recommended.  Proceed at your own risk."
        else:
            fromcog = True
            extra = ""

        def check(m):
            return (
                (m.author.id == ctx.author.id)
                and (m.channel.id == ctx.channel.id)
                and (m.content[0].lower() in ["y", "n"])
            )

        await ctx.send(
            (
                "You are about to remove a cooldown for a command.  "
                "Are you sure you wish to remove it?  Respond with 'y' or 'n' to this message."
                f"{extra}"
            )
        )
        try:
            m = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long to respond.")
        if m.content.lower().startswith("y"):
            commands.cooldown(10000, 1, dc.BucketType.user)(cmd)
        else:
            return await ctx.send("Not removing command cooldown.")
        if fromcog:
            for entry in data:
                if entry[0] == command:
                    data.remove(entry)
                    break
        else:
            data.append([command, 10000, 1, "global"])
        await self.conf.data.set(data)

        await ctx.send(
            "Your cooldown has been removed.  If this cog originally had a cooldown, then you removed/edited it, and you just removed it, a bot restart is required for the original cooldown to be instated."
        )
