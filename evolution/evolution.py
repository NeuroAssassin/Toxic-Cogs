from redbot.core import commands, Config, bank, checks, errors
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_number, humanize_timedelta, inline
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils import AsyncIter
from collections import defaultdict
from datetime import timedelta
import copy
import asyncio
import random
import discord
import math
import traceback

from .utils import EvolutionUtils
from .tasks import EvolutionTaskManager

ANIMALS = ["chicken", "dog", "cat", "shark", "tiger", "penguin", "pupper", "dragon"]


class Evolution(commands.Cog):
    """EVOLVE THOSE ANIMALS!!!!!!!!!!!"""

    def __init__(self, bot):
        self.bot: Red = bot
        self.lock = asyncio.Lock()
        self.conf: Config = Config.get_conf(self, identifier=473541068378341376)
        self.cache = defaultdict(self.cache_defaults)  # Thanks to Theelx#4980

        self.utils: EvolutionUtils = EvolutionUtils(self)
        self.task_manager: EvolutionTaskManager = EvolutionTaskManager(self)

        self.utils.init_config()
        self.task_manager.init_tasks()

        self.inmarket = []

    def cache_defaults(self):
        return {"animal": "", "animals": {}, "multiplier": 1.0, "bought": {}}

    def cog_unload(self):
        self.__unload()

    def __unload(self):
        self.cache.clear()
        self.task_manager.shutdown()

    @commands.group(aliases=["e", "evo"])
    async def evolution(self, ctx):
        """EVOLVE THE GREATEST ANIMALS OF ALL TIME!!!!"""
        pass

    @checks.is_owner()
    @evolution.group()
    async def tasks(self, ctx):
        """View the status of the cog tasks.

        These are for debugging purposes"""
        pass

    @tasks.command(aliases=["checkdelivery", "cd"])
    async def income(self, ctx):
        """Check the delivery status of your money.

        In reality terms, check to see if the income background task has run into an issue"""
        statuses = self.task_manager.get_statuses()
        message = self.utils.format_task(statuses["income"])
        await ctx.send(message)

    @checks.is_owner()
    @evolution.command(hidden=True)
    async def removeuser(self, ctx, user: discord.User):
        """Removes a user from the market place if they are stuck for some reason.
        
        Only use this if you have to, otherwise things could break"""
        try:
            self.inmarket.remove(user.id)
        except ValueError:
            return await ctx.send("The user is not in the marketplace")
        await ctx.tick()

    @evolution.command()
    async def start(self, ctx):
        """Start your adventure..."""
        # No locks are needed here because they are all being used with values that don't change,
        # or shouldn't be changing at the moment
        animal = await self.conf.user(ctx.author).animal()
        if animal != "":
            return await ctx.send("You have already started your evolution.")
        if animal == "P":
            return await ctx.send("You are starting your evolution.")
        async with self.lock:
            await self.conf.user(ctx.author).animal.set("P")
        await ctx.send(
            f"Hello there.  Welcome to Evolution, where you can buy animals to earn credits for economy.  What would you like your animals to be named (singular please)?  Warning: this cannot be changed.  Here is a list of the current available ones: `{'`, `'.join(ANIMALS)}`"
        )

        def check(m):
            return (
                (m.author.id == ctx.author.id)
                and (m.channel.id == ctx.channel.id)
                and (m.content.lower() in ANIMALS)
            )

        try:
            message = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            async with self.lock:
                await self.conf.user(ctx.author).animal.set("")
            return await ctx.send("Command timed out.")
        async with self.lock:
            async with self.conf.user(ctx.author).all() as data:
                data["animal"] = message.content.lower()
                data["animals"] = {1: 1}

                self.cache[ctx.author.id] = data
        await ctx.send(
            f"Your animal has been set to {message.content}.  You have been granted one to start."
        )

    @evolution.command()
    async def buy(self, ctx, level: int, amount: int = 1, skip_confirmation: bool = False):
        """Buy those animals to get more economy credits"""
        if ctx.author.id in self.inmarket:
            return await ctx.send("You're already at the market")
        self.inmarket.append(ctx.author.id)
        async with self.lock:
            data = await self.conf.user(ctx.author).all()
        animals = data["animals"]
        bought = data["bought"]
        animal = data["animal"]
        multiplier = data["multiplier"]

        if animal in ["", "P"]:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("Finish starting your evolution first")

        highest = max(list(map(int, animals.keys())))
        prev = int(animals.get(str(level), 0))
        balance = await bank.get_balance(ctx.author)
        current_bought = int(bought.get(str(level), 0))
        price = self.utils.get_total_price(level, current_bought, amount)

        e = math.ceil((multiplier - 1) * 5)

        if balance < price:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send(f"You need {humanize_number(price)} credits for all of that!")
        if prev >= 6 + e:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("You have too many of those!  Evolve some of them already.")
        if prev + amount > 6 + e:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("You'd have too many of those!  Evolve some of them already.")
        if level < 1:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("Ya cant buy a negative level!")
        if amount < 1:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("Ya cant buy a negative amount!")
        if (level > int(highest) - 3) and (level > 1):
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("Please get higher animals to buy higher levels of them.")

        if not skip_confirmation:
            m = await ctx.send(
                f"Are you sure you want to buy {amount} Level {str(level)} {animal}{'s' if amount != 1 else ''}?  This will cost you {humanize_number(price)}."
            )
            await m.add_reaction("\N{WHITE HEAVY CHECK MARK}")
            await m.add_reaction("\N{CROSS MARK}")

            def check(reaction, user):
                return (
                    (user.id == ctx.author.id)
                    and (str(reaction.emoji) in ["\N{WHITE HEAVY CHECK MARK}", "\N{CROSS MARK}"])
                    and (reaction.message.id == m.id)
                )

            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=60.0)
            except asyncio.TimeoutError:
                self.inmarket.remove(ctx.author.id)
                return await ctx.send(f"You left the {animal} shop without buying anything.")

            if str(reaction.emoji) == "\N{CROSS MARK}":
                self.inmarket.remove(ctx.author.id)
                return await ctx.send(f"You left the {animal} shop without buying anything.")
        animals[str(level)] = prev + amount
        bought[level] = current_bought + 1

        async with self.lock:
            async with self.conf.user(ctx.author).all() as data:
                data["animals"] = animals
                data["bought"] = bought

                self.cache[ctx.author.id] = data

        await bank.withdraw_credits(ctx.author, price)
        await ctx.send(
            f"You bought {amount} Level {str(level)} {animal}{'s' if amount != 1 else ''}"
        )
        self.inmarket.remove(ctx.author.id)

    @checks.bot_has_permissions(embed_links=True)
    @evolution.command()
    async def shop(self, ctx, start_level: int = None):
        """View them animals in a nice little buying menu"""
        async with self.lock:
            data = await self.conf.user(ctx.author).all()
        animals = data["animals"]
        bought = data["bought"]
        animal = data["animal"]

        if animal in ["", "P"]:
            return await ctx.send("Finish starting your evolution first")

        embed_list = []
        for x in range(1, max(list(map(int, animals.keys()))) + 1):
            embed = discord.Embed(
                title=f"{animal.title()} Shop", description=f"Level {str(x)}", color=0xD2B48C,
            )
            embed.add_field(name="You currently own", value=animals.get(str(x), 0))
            current = int(bought.get(str(x), 0))
            embed.add_field(name="You have bought", value=current)
            embed.add_field(
                name="Price", value=humanize_number(self.utils.get_total_price(int(x), current, 1))
            )
            last = 0
            chances = []
            try:
                for chance, value in self.utils.levels[int(x)].items():
                    chances.append(f"{str(chance-last)}% chance to gain {str(value)}")
                    last = chance
            except KeyError:
                chances = ["100% chance to gain 1000"]
            embed.add_field(name="Income", value="\n".join(chances))
            embed.add_field(
                name="Credit delay",
                value=humanize_timedelta(timedelta=timedelta(seconds=self.utils.delays[int(x)])),
            )
            embed_list.append(embed)

        highest_level = max([int(a) for a in animals.keys() if int(animals[a]) > 0])
        highest_level -= 3
        if start_level:
            highest_level = start_level

        highest_level -= 1

        controls = copy.deepcopy(DEFAULT_CONTROLS)
        controls["\N{MONEY BAG}"] = self.utils.shop_control_callback
        await menu(ctx, embed_list, controls, page=highest_level)

    @checks.bot_has_permissions(embed_links=True)
    @evolution.command(aliases=["by"])
    async def backyard(self, ctx, use_menu: bool = False):
        """Where ya animals live!  Pass 1 or true to put it in a menu."""
        async with self.lock:
            data = await self.conf.user(ctx.author).all()
        animal = data["animal"]
        animals = data["animals"]
        multiplier = data["multiplier"]
        e = 6 + math.ceil((multiplier - 1) * 5)

        if animal in ["", "P"]:
            return await ctx.send("Finish starting your evolution first")

        if use_menu:
            embed_list = []
            for level, amount in animals.items():
                if amount == 0:
                    continue
                embed = discord.Embed(
                    title=f"Level {str(level)} {animal}",
                    description=f"You have {str(amount)} Level {level} {animal}{'s' if amount != 1 else ''}",
                    color=0xD2B48C,
                )
                embed_list.append(embed)
            await menu(ctx, embed_list, DEFAULT_CONTROLS)
        else:
            embed = discord.Embed(
                title=f"The amount of {animal}s you have in your backyard.",
                color=0xD2B48C,
                description=f"Multiplier: {inline(str(multiplier))}\nMax amount of animals: {inline(str(e))}",
            )
            for level, amount in animals.items():
                if amount == 0:
                    continue
                embed.add_field(
                    name=f"Level {str(level)} {animal}",
                    value=f"You have {str(amount)} Level {level} {animal}{'s' if amount != 1 else ''} \N{ZERO WIDTH SPACE} \N{ZERO WIDTH SPACE}",
                )
            await ctx.send(embed=embed)

    @evolution.command()
    async def evolve(self, ctx, level: int, amount: int = 1):
        """Evolve them animals to get more of da economy credits"""
        if ctx.author.id in self.inmarket:
            return await ctx.send("Leave the market before evolving your animals")
        self.inmarket.append(ctx.author.id)
        if level < 1 or amount < 1:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("Too low!")

        async with self.lock:
            data = await self.conf.user(ctx.author).all()
        animal = data["animal"]
        animals = data["animals"]
        multiplier = data["multiplier"]

        e = math.ceil((multiplier - 1) * 5)

        if amount > (6 + e) // 2:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("Too high!")

        if animal in ["", "P"]:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("Finish starting your evolution first")

        current = animals.get(str(level), 0)
        highest = max(list(map(int, animals.keys())))
        nextlevel = animals.get(str(level + 1), 0)

        if current < (amount * 2):
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("You don't have enough animals at that level.")

        if nextlevel + amount > 6 + e:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send(
                f"You'd have too many Level {str(level + 1)}s!  Evolve some of them instead!"
            )

        found_new = False
        recreate = False
        currentlevelstr = str(level)
        nextlevelstr = str(level + 1)

        animals[currentlevelstr] -= 2 * amount
        if highest == level:
            found_new = True
        animals[nextlevelstr] = animals.get(nextlevelstr, 0) + amount
        if level + 1 == 26:
            recreate = True

        if found_new:
            sending = "\nCONGRATULATIONS!  You have found a new animal!"
        else:
            sending = ""
        await ctx.send(
            f"Successfully converted {str(amount * 2)} Level {currentlevelstr} {animal}s into {str(amount)} Level {nextlevelstr} {animal}{'s' if amount != 1 else ''}{sending}"
        )
        if recreate:
            async with self.lock:
                async with self.conf.user(ctx.author).all() as data:
                    multiplier = data["multiplier"]
                    data["animals"] = {1: 1}
                    data["multiplier"] = multiplier + 0.2
            new = (
                "**Report:**\n"
                f"**To:** {ctx.author.display_name}\n"
                f"**Concerning:** Animal experiment #{str(math.ceil(((multiplier - 1) * 5) + 1))}\n"
                f"**Subject:** Animal experiment concluded.\n\n"
                f"Congratulations, {ctx.author.display_name}!  You have successfully combined enough animals to reach a Level 26 Animal!  This means that it is time to recreate universe!  This will give you a boost of 50,000 credits, remove all of your animals, allow one more animal of every level, and give you an extra 20% income rate for the next universe from all income.  Congratulations!\n\n"
                f"From, The Head {animal.title()}"
            )
            await ctx.send(new)
            await bank.deposit_credits(ctx.author, 50000)
        else:
            async with self.lock:
                await self.conf.user(ctx.author).animals.set(animals)
        self.inmarket.remove(ctx.author.id)

    @checks.admin()
    @evolution.group(disabled=True)
    async def traveler(self, ctx):
        """Manage how often the traveler comes, and where he comes"""
        pass

    @checks.is_owner()
    @traveler.command()
    async def delay(self, ctx):
        """Set how long it takes for the Traveler to come"""
        pass
