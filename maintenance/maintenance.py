from redbot.core import commands, checks, Config
from datetime import datetime
import discord
import time


class Maintenance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=473541068378341376)
        default_global = {
            "on": [False, 0, []],
            "message": "The bot is undergoing maintenance.  Please check back later.",
            "delete": 3,
        }
        # When on maintenance, on will be set to [True, second of when it is off maintenance, list of people who can bypass the maintenance]
        self.conf.register_global(**default_global)
        self.bot.add_check(self.cog_check)

    def __unload(self):
        self.bot.remove_check(self.cog_check)

    async def cog_check(self, ctx):
        on = await self.conf.on()
        if not on[0]:
            return True
        if on[1] <= time.time() and on[1] != 0:
            setting = [False, 0, []]
            await self.conf.on.set(setting)
            return True
        on[2].append(self.bot.owner_id)
        if ctx.author.id in on[2]:
            return True
        message = await self.conf.message()
        delete = await self.conf.delete()
        if delete != 0:
            await ctx.send(message, delete_after=delete)
        else:
            await ctx.send(message)
        return False

    @checks.is_owner()
    @commands.group()
    async def maintenance(self, ctx):
        """Control the bot's maintenance."""
        pass

    @maintenance.command(name="on")
    async def _on(self, ctx, *, args=None):
        """Puts the bot on maintenance, preventing everyone but you from running commands.  Other people will just be told the bot is currently on maintenance.
        
        You can specify arguments by seperating them from each other by a space.  Any argument that ends with an alphabetical letter will be considered as the time for when the maintenance will end.  If there is none, `[p]maintenance clear` will need to be used to remove the maintenance.  All other paramaters will be considered user IDs that can bypass the maintenance.
        
        For specifying the time, please end with an alphabetical letter, of one of the following:
            S => Seconds
            M = Minutes
            H => Hours
            D => Days
            W => Weeks
            
        For example, `1s` for one second, `5m` for five minutes, etc."""
        on = await self.conf.on()
        if args == None:
            args = []
        if on[0]:
            return await ctx.send(
                f"The bot is already on maintenance.  Please clear with `{ctx.prefix}maintenance off`"
            )
        args = args.split(" ") if hasattr(args, "split") else args
        num = None
        whitelist = []
        for arg in args:
            if arg[-1].isalpha():
                num = int(arg[:-1])
                arg = arg.lower()
                if arg.endswith("m"):
                    num *= 60
                elif arg.endswith("h"):
                    num *= 3600
                elif arg.endswith("d"):
                    num *= 86400
                elif arg.endswith("w"):
                    num *= 604800
                elif arg.endswith("s"):
                    pass
                else:
                    return await ctx.send(
                        "You provided a time ending for the arguments, but an invalid timing letter.  Please use either s, m, h, d or w."
                    )
            else:
                arg = int(arg)
                user = self.bot.get_user(arg)
                if not user:
                    return await ctx.send(f"Invalid User ID: {arg}")
                whitelist.append(arg)
        if not num:
            num = 0
        else:
            num += time.time()
        setting = [True, num, whitelist]
        await self.conf.on.set(setting)
        await ctx.tick()

    @maintenance.command()
    async def settings(self, ctx):
        """Tells the current settings of the cog."""
        on = await self.conf.on()
        message = await self.conf.message()
        delete = await self.conf.delete()
        sending = (
            f"Messages are deleted after {delete} seconds.  "
            f"Your current disabled message is ```{message}```"
        )
        if not on[0]:
            sending += "The bot is currently not on maintenance."
            return await ctx.send(sending)
        if on[1] != 0:
            done = str(datetime.fromtimestamp(on[1]).strftime("%A, %B %d, %Y %I:%M:%S"))
            done = "on " + done
        else:
            done = "when the bot owner removes it from maintenance"
        users = []
        for user in on[2]:
            user_profile = await self.bot.get_user_info(user)
            users.append(user_profile.display_name) if hasattr(
                user_profile, "display_name"
            ) else users.append(f"<removed user {user}>")
        sending += (
            "The bot is currently under maintenance.  "
            f"It will be done {str(done)}.  "
            f"The following users are whitelisted from the maintenance: `{'` `'.join(users)}`"
        )
        await ctx.send(sending)

    @maintenance.command()
    async def off(self, ctx):
        """Clears the bot from maintenance"""
        on = await self.conf.on()
        if not on[0]:
            return await ctx.send("The bot is not on maintenance.")
        setting = [False, 0, []]
        await self.conf.on.set(setting)
        await ctx.tick()

    @maintenance.command()
    async def message(self, ctx, *, message):
        """Set the message sent when the bot is down for maintenance"""
        await self.conf.message.set(message)
        await ctx.tick()

    @maintenance.command()
    async def deleteafter(self, ctx, amount: int = 0):
        """Set the amount of seconds before the maintenance message is deleted.  Pass no parameter or 0 to make it not delete the message"""
        await self.conf.delete.set(amount)
        await ctx.tick()

    @maintenance.command()
    async def whitelist(self, ctx, user: discord.User):
        """Remove or add a person from or to the whitelist for the current maintenance"""
        on = await self.conf.on()
        if user.id in on[2]:
            on[2].remove(user.id)
            message = f"{user.display_name} has been removed from the whitelist."
        else:
            on[2].append(user.id)
            message = f"{user.display_name} has been added to the whitelist."
        await self.conf.on.set(on)
        await ctx.send(message)