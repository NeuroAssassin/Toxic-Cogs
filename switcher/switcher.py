from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import pagify
from discord.ext import commands as ext
import discord
import asyncio
import tabulate

CHECK = "\N{WHITE HEAVY CHECK MARK}"
XEMOJI = "\N{NEGATIVE SQUARED CROSS MARK}"


class Switcher(commands.Cog):
    """Switch between bot accounts easily while maintaning the current bot's data"""

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=473541068378341376)
        self.conf.register_global(**{"data": {}})

    async def add_reactions(self, m):
        await m.add_reaction(CHECK)
        await m.add_reaction(XEMOJI)

    @checks.is_owner()
    @commands.group()
    async def switcher(self, ctx):
        """Switch between bots just by using a command."""
        pass

    @switcher.command()
    async def add(self, ctx, bot_name, token):
        """Add a bot to Switcher to switch between.

        Only use this in DMs so your token doesn't get leaked.
        
        The command will attempt to log in via the token to ensure the token is valid."""
        if ctx.guild:
            try:
                await ctx.message.delete()
                deleted = True
            except:
                deleted = False
                pass
            sending = "WARNING!  You just tried to use the command in a guild, and now your token may be leaked.  It is recommended to head over to the developer console and change it immediately.  "
            if deleted:
                sending += "Your message was deleted, so it's possible no one saw it, but it's better to be safe than sorry."
            else:
                sending += "You should also delete your message, as I was unable to do so."
            return await ctx.send(sending)
        new_bot = ext.Bot(command_prefix="Switcher")
        try:
            await new_bot.login(token)
        except discord.errors.LoginFailure:
            await ctx.send("Invalid token.  Please ensure you typed everything correctly")
        else:
            data = await self.conf.data()
            if bot_name in list(data.keys()):
                await ctx.send("This bot name is already registered.")
            else:
                if token in list(data.values()):
                    await ctx.send("This token is already registered.")
                else:
                    data[bot_name] = token
                    await self.conf.data.set(data)
                    await ctx.tick()
        finally:
            await new_bot.logout()

    @switcher.command()
    async def run(self, ctx, bot_name):
        """Sets up the bot to change to the bot specified via the name"""
        data = await self.conf.data()
        if not bot_name in data:
            return await ctx.send("Invalid bot name.")
        # Just to make sure
        token = data[bot_name]
        new_bot = ext.Bot(command_prefix="Switcher")
        try:
            await new_bot.login(token)
        except discord.errors.LoginFailure:
            await new_bot.logout()
            return await ctx.send("Invalid token.  Is it possible you refreshed the token?")
        await new_bot.logout()

        def check(reaction, user):
            return (user.id == ctx.author.id) and (str(reaction.emoji) in [CHECK, XEMOJI])

        m = await ctx.send("Are you sure you want to do this?")
        await self.add_reactions(m)
        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("Not running.")
        if str(reaction.emoji) == XEMOJI:
            return await ctx.send("Not running.")

        await self.bot._config.token.set(token)
        m = await ctx.send("Token updated.\nWould you like to restart?")
        await self.add_reactions(m)

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send(
                "Not restarting.  Bot change will happen on the next restart.  Do not change your token or the bot will fail to start."
            )
        if str(reaction.emoji) == CHECK:
            await ctx.invoke(self.bot.get_command("restart"))
        else:
            await ctx.send(
                "Not restarting.  Bot change will happen on the next restart.  Do not change your token or the bot will fail to start."
            )

    @switcher.command(name="list", usage=" ")
    async def _list(self, ctx, show_tokens: bool = False):
        """List the current bot's saved tokens in the cog."""
        if ctx.guild:
            show_tokens = False
        data = await self.conf.data()
        headers = ["Bot name"]
        if show_tokens:
            headers.append("Token")
        sending = []
        for name, token in data.items():
            setting = [name]
            if show_tokens:
                setting.append(token)
            sending.append(setting)
        string = tabulate.tabulate(sending, headers=headers, tablefmt="psql")
        for page in pagify(string, delims=["\n"], shorten_by=10):
            await ctx.send("```\n" + page + "```")

    @switcher.command()
    async def remove(self, ctx, bot_name):
        """Removes a bot from Switcher's tracked bots."""
        data = await self.conf.data()
        if not bot_name in data:
            return await ctx.send("That bot isn't stored.")

        def check(reaction, user):
            return (user.id == ctx.author.id) and (str(reaction.emoji) in [CHECK, XEMOJI])

        m = await ctx.send("Are you sure you want to remove this bot?")
        await self.add_reactions(m)

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("Not removing bot.")
        if str(reaction.emoji) == XEMOJI:
            return await ctx.send("Not removing bot.")
        del data[bot_name]
        await self.conf.data.set(data)
        await ctx.tick()

    @switcher.command()
    async def edit(self, ctx, bot_name, token):
        """Edit the token for the specified bot.
        
        Only use this in DMs so your token doesn't get leaked."""
        if ctx.guild:
            try:
                await ctx.message.delete()
                deleted = True
            except:
                deleted = False
                pass
            sending = "WARNING!  You just tried to use the command in a guild, and now your token may be leaked.  It is recommended to head over to the developer console and change it immediately.  "
            if deleted:
                sending += "Your message was deleted, so it's possible no one saw it, but it's better to be safe than sorry."
            else:
                sending += "You should also delete your message, as I was unable to do so."
            return await ctx.send(sending)
        data = await self.conf.data()
        if not bot_name in data:
            return await ctx.send("That bot isn't stored.")

        new_bot = ext.Bot(command_prefix="Switcher")
        try:
            await new_bot.login(token)
        except discord.errors.LoginFailure:
            await new_bot.logout()
            return await ctx.send("Invalid token.")
        await new_bot.logout()

        def check(reaction, user):
            return (user.id == ctx.author.id) and (str(reaction.emoji) in [CHECK, XEMOJI])

        m = await ctx.send("Are you sure you want to do this?")
        await self.add_reactions(m)
        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("Not changing token.")
        if str(reaction.emoji) == XEMOJI:
            return await ctx.send("Not changing token.")

        data[bot_name] = token
        await self.conf.data.set(data)
        await ctx.tick()
