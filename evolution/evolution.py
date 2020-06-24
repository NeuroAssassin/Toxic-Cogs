from redbot.core import commands, Config, bank, checks, errors
from redbot.core.utils.chat_formatting import humanize_number, inline
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils import AsyncIter
from collections import defaultdict
import copy
import asyncio
import random
import discord
import math
import traceback

ANIMALS = ["chicken", "dog", "cat", "shark", "tiger", "penguin", "pupper", "dragon"]

LEVELS = {
    1: {80: 1, 100: 10},
    2: {60: 1, 100: 10},
    3: {50: 1, 90: 10, 100: 100},
    4: {30: 1, 70: 10, 100: 100},
    5: {10: 1, 60: 10, 100: 100},
    6: {40: 10, 100: 100},
    7: {20: 10, 90: 100, 100: 1000},
    8: {80: 100, 100: 1000},
    9: {60: 100, 100: 1000},
    10: {50: 100, 100: 1000},
    11: {40: 100, 100: 1000},
    12: {30: 100, 100: 1000},
    13: {20: 100, 100: 1000},
    14: {10: 100, 100: 1000},
    15: {100: 1000},
}

IMAGES = {
    "shark": "https://www.bostonmagazine.com/wp-content/uploads/sites/2/2019/05/Great-white-shark.jpg",
    "chicken": "https://i1.wp.com/thechickhatchery.com/wp-content/uploads/2018/01/RI-White.jpg?fit=371%2C363&ssl=1",
    "penguin": "https://cdn.britannica.com/77/81277-050-2A6A35B2/Adelie-penguin.jpg",
    "dragon": "https://images-na.ssl-images-amazon.com/images/I/61NTUxEnn0L._SL1032_.jpg",
    "tiger": "https://c402277.ssl.cf1.rackcdn.com/photos/18134/images/hero_small/Medium_WW226365.jpg?1574452099",
    "cat": "https://icatcare.org/app/uploads/2018/07/Thinking-of-getting-a-cat.png",
    "dog": "https://d17fnq9dkz9hgj.cloudfront.net/breed-uploads/2018/09/dog-landing-hero-lg.jpg?bust=1536935129&width=1080",
    "pupper": "https://i.ytimg.com/vi/MPV2METPeJU/maxresdefault.jpg"
}


class Evolution(commands.Cog):
    """EVOLVE THOSE ANIMALS!!!!!!!!!!!"""

    def __init__(self, bot):
        self.bot = bot
        self.lock = asyncio.Lock()

        self.conf = Config.get_conf(self, identifier=473541068378341376)
        default_user = {"animal": "", "animals": {}, "multiplier": 1.0, "bought": {}}
        self.conf.register_user(**default_user)
        self.cache = defaultdict(self.cache_defaults)  # Thanks to Theelx#4980

        self.inmarket = []
        self.task = self.bot.loop.create_task(self.bg_task())

    def cache_defaults(self):
        return {"animal": "", "animals": {}, "multiplier": 1.0, "bought": {}}

    def cog_unload(self):
        self.__unload()

    def __unload(self):
        self.cache.clear()
        self.task.cancel()

    async def initialize(self):
        config = await self.conf.all_users()
        for k, v in config.items():
            self.cache[k] = v

    async def bg_task(self):
        await self.bot.wait_until_ready()
        while True:
            for userid, data in self.cache.copy().items():
                animal = data["animal"]
                if animal == "":
                    continue
                multiplier = data["multiplier"]
                animals = data["animals"]
                all_gaining = 0
                for key, value in animals.items():
                    for x in range(0, value):
                        chance = random.randint(1, 100)
                        try:
                            chances = list(LEVELS[int(key)].keys())
                        except:
                            chances = [100]
                        chosen = min([c for c in chances if chance <= c])
                        try:
                            gaining = LEVELS[int(key)][chosen]
                        except:
                            gaining = 1000
                        gaining *= multiplier
                        all_gaining += gaining * 0.5
                user = self.bot.get_user(userid)
                if user is None:
                    user = await self.bot.fetch_user(userid)  # Prepare to be rate limited :aha:
                if user:
                    try:
                        await bank.deposit_credits(user, math.ceil(all_gaining))
                    except errors.BalanceTooHigh:
                        # Welp, they need to evolve stuff
                        pass
                await asyncio.sleep(0.1)
            await asyncio.sleep(60)

    def get_total_price(self, level, bought, amount):
        total = 0
        for x in range(amount):
            normal = level * 800
            level_tax = ((2 ** level) * 100) - 200
            tax = bought * 300
            total += normal + level_tax + tax + (x * 300)
        return total

    async def shop_control_callback(self, ctx, pages, controls, message, page, timeout, emoji):
        description = message.embeds[0].description
        level = int(description.split(" ")[1])
        self.bot.loop.create_task(ctx.invoke(self.buy, level=level))
        return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)

    @commands.group(aliases=["e", "evo"])
    async def evolution(self, ctx):
        """EVOLVE THE GREATEST ANIMALS OF ALL TIME!!!!"""
        pass

    @checks.is_owner()
    @evolution.command(aliases=["cd"])
    async def checkdelivery(self, ctx):
        """Check the delivery status of your money.

        In reality terms, check to see if the background tasks have run into an issue"""
        message = "Task is currently "
        cancelled = self.task.cancelled()
        if cancelled:
            message += "canceled."
        else:
            done = self.task.done()
            if done:
                message += "done."
            else:
                message += "running."
        try:
            e = self.task.exception()
        except asyncio.exceptions.InvalidStateError:
            message += "  No error has been encountered."
        else:
            ex = traceback.format_exception(type(e), e, e.__traceback__)
            message += f"  An error has been encountered.  Please report the following to Neuro Assassin on the help server. ```py\n{''.join(ex)}```"
        if len(message) > 2000:
            message = message[:1994] + "...```"
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
    async def buy(self, ctx, level: int, amount: int = 1):
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
        price = self.get_total_price(level, current_bought, amount)

        e = math.ceil((multiplier - 1) * 5)

        if balance < price:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("You don't have enough credits!")
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
    async def shop(self, ctx):
        """View them animals in a nice little buying menu"""
        async with self.lock:
            data = await self.conf.user(ctx.author).all()
        animals = data["animals"]
        bought = data["bought"]
        animal = data["animal"]

        if animal in ["", "P"]:
            return await ctx.send("Finish starting your evolution first")

        embed_list = []
        for x in list(animals.keys()):
            embed = discord.Embed(
                title=f"{animal.title()} Shop", description=f"Level {str(x)}", color=0xD2B48C,
            )
            embed.add_field(name="You currently own", value=animals[x])
            current = int(bought.get(str(x), 0))
            embed.add_field(name="You have bought", value=current)
            embed.add_field(
                name="Price", value=humanize_number(self.get_total_price(int(x), current, 1))
            )
            last = 0
            chances = []
            try:
                for chance, value in LEVELS[int(x)].items():
                    chances.append(f"{str(chance-last)}% chance to gain {str(value)}")
                    last = chance
            except KeyError:
                chances = ["100% chance to gain 1000"]
            embed.add_field(name="Income", value="\n".join(chances))
            embed_list.append(embed)
        controls = copy.deepcopy(DEFAULT_CONTROLS)
        controls["\N{MONEY BAG}"] = self.shop_control_callback
        await menu(ctx, embed_list, controls)

    @checks.bot_has_permissions(embed_links=True)
    @evolution.command()
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
                embed.set_thumbnail(url=IMAGES[animal])
                embed_list.append(embed)
            await menu(ctx, embed_list, DEFAULT_CONTROLS)
        else:
            embed = discord.Embed(
                title=f"The amount of {animal}s you have in your backyard.",
                color=0xD2B48C,
                description=f"Multiplier: {inline(str(multiplier))}\nMax amount of animals: {inline(str(e))}",
            )
            embed.set_thumbnail(url=IMAGES[animal])
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
            return await ctx.send("You'd have to many of those!  Evolve some of them instead!")

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
