from redbot.core import commands, Config, bank, checks
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
import copy
import asyncio
import random
import discord
import math

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


class Evolution(commands.Cog):
    """EVOLVE THOSE ANIMALS!!!!!!!!!!!"""

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=473541068378341376)
        default_user = {"animal": "", "animals": {}, "multiplier": 1.0, "bought": {}}
        self.conf.register_user(**default_user)
        self.money_task = self.bot.loop.create_task(self.bg_task())
        self.gain_task = self.bot.loop.create_task(self.gain_bg_task())

    def cog_unload(self):
        self.__unload()

    def __unload(self):
        self.money_task.cancel()
        self.gain_task.cancel()

    async def gain_bg_task(self):
        await self.bot.wait_until_ready()
        while True:
            users = await self.conf.all_users()
            for user, data in users.items():
                animals = data["animals"]
                animal = data["animal"]
                if animal == "":
                    continue
                prev = int(animals.get("1", 0))
                if prev < 6:
                    animals["1"] = prev + 1
                await asyncio.sleep(0.1)
                try:
                    user = await self.bot.get_user_info(user)
                except AttributeError:
                    user = await self.bot.fetch_user(user)
                if user:
                    await self.conf.user(user).animals.set(animals)
            await asyncio.sleep(600)

    async def bg_task(self):
        await self.bot.wait_until_ready()
        while True:
            users = await self.conf.all_users()
            for user, data in users.items():
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
                        all_gaining += gaining
                try:
                    user = await self.bot.get_user_info(user)
                except AttributeError:
                    user = await self.bot.fetch_user(user)
                if user:
                    await bank.deposit_credits(user, math.ceil(all_gaining))
                await asyncio.sleep(0.1)
            await asyncio.sleep(60)

    def get_level_tax(self, level):
        if level == 1:
            return 0
        return (self.get_level_tax(level - 1) * 2) + 200

    def get_total_price(self, level, bought, amount):
        total = 0
        for x in range(amount):
            normal = level * 800
            level_tax = self.get_level_tax(level)
            tax = bought * 300
            total += normal + level_tax + tax + (x * 300)
        return total

    async def shop_control_callback(self, ctx, pages, controls, message, page, timeout, emoji):
        description = message.embeds[0].description
        level = int(description.split(" ")[1])
        await ctx.invoke(self.buy, level=level)

    @commands.group(aliases=["e", "evo"])
    async def evolution(self, ctx):
        """EVOLVE THE GREATEST ANIMALS OF ALL TIME!!!!"""
        pass

    @evolution.command()
    async def start(self, ctx):
        """Start your adventure..."""
        animal = await self.conf.user(ctx.author).animal()
        if animal != "":
            return await ctx.send("You have already started your evolution.")
        if animal == "P":
            return await ctx.send("You are starting your evolution.")
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
            await self.conf.user(ctx.author).animal.set("")
            return await ctx.send("Command timed out.")
        await self.conf.user(ctx.author).animal.set(message.content.lower())
        await ctx.send(
            f"Your animal has been set to {message.content}.  You have been granted one to start."
        )
        await self.conf.user(ctx.author).animals.set({1: 1})

    @evolution.command()
    async def buy(self, ctx, level: int, amount: int = 1):
        """Buy those animals to get more economy credits"""
        animal = await self.conf.user(ctx.author).animal()
        if animal in ["", "P"]:
            return await ctx.send("Finish starting your evolution first")
        animals = await self.conf.user(ctx.author).animals()
        highest = max(list(map(int, animals.keys())))
        prev = int(animals.get(str(level), 0))
        balance = await bank.get_balance(ctx.author)
        bought = await self.conf.user(ctx.author).bought()
        current_bought = int(bought.get(str(level), 0))
        price = self.get_total_price(level, current_bought, amount)
        if balance < price:
            return await ctx.send("You don't have enough credits!")
        if prev >= 6:
            return await ctx.send("You have too many of those!  Evolve some of them already.")
        if prev + amount > 6:
            return await ctx.send("You'd have too many of those!  Evolve some of them already.")
        if level < 1:
            return await ctx.send("Ya cant buy a negative level!")
        if amount < 1:
            return await ctx.send("Ya cant buy a negative amount!")
        if (level > int(highest) - 3) and (level > 1):
            return await ctx.send("Please get higher animals to buy higher levels of them.")
        m = await ctx.send(
            f"Are you sure you want to buy {amount} Level {str(level)} {animal}{'s' if amount != 1 else ''}?  This will cost you {str(price)}."
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
            return await ctx.send(f"You left the {animal} shop without buying anything.")
        if str(reaction.emoji) == "\N{CROSS MARK}":
            return await ctx.send(f"You left the {animal} shop without buying anything.")
        animals[str(level)] = prev + amount
        await self.conf.user(ctx.author).animals.set(animals)
        await bank.withdraw_credits(ctx.author, price)
        bought[level] = current_bought + 1
        await self.conf.user(ctx.author).bought.set(bought)
        await ctx.send(
            f"You bought {amount} Level {str(level)} {animal}{'s' if amount != 1 else ''}"
        )

    @checks.bot_has_permissions(embed_links=True)
    @evolution.command()
    async def shop(self, ctx):
        """View them animals in a nice little buying menu"""
        animal = await self.conf.user(ctx.author).animal()
        if animal in ["", "P"]:
            return await ctx.send("Finish starting your evolution first")
        animals = await self.conf.user(ctx.author).animals()
        bought = await self.conf.user(ctx.author).bought()
        embed_list = []
        for x in list(animals.keys()):
            embed = discord.Embed(
                title=f"{animal.title()} Shop", description=f"Level {str(x)}", color=0xD2B48C
            )
            embed.add_field(name="You currently own", value=animals[x])
            current = int(bought.get(str(x), 0))
            embed.add_field(name="You have bought", value=current)
            embed.add_field(name="Price", value=self.get_total_price(int(x), current, 1))
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
        animal = await self.conf.user(ctx.author).animal()
        if animal in ["", "P"]:
            return await ctx.send("Finish starting your evolution first")
        animals = await self.conf.user(ctx.author).animals()
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
                title=f"The amount of {animal}s you have in your backyard.", color=0xD2B48C
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
        if level < 1 or amount < 1:
            return await ctx.send("Too low!")
        if amount > 3:
            return await ctx.send("Too high!")
        animal = await self.conf.user(ctx.author).animal()
        if animal in ["", "P"]:
            return await ctx.send("Finish starting your evolution first")
        animals = await self.conf.user(ctx.author).animals()
        current = animals.get(str(level), 0)
        highest = max(list(map(int, animals.keys())))
        if current < (amount * 2):
            return await ctx.send("You don't have enough animals at that level.")
        counter = 0
        found_new = False
        recreate = False
        for x in range(amount):
            animals[str(level)] -= 2
            prev = animals.get(str(level + 1), 0)
            if prev == 6:
                continue
            if highest == level:
                found_new = True
            animals[str(level + 1)] = animals.get(str(level + 1), 0) + 1
            await self.conf.user(ctx.author).animals.set(animals)
            counter += 2
            if level + 1 == 26:
                recreate = True
        if found_new:
            sending = "\nCONGRATULATIONS!  You have found a new animal!"
        else:
            sending = ""
        await ctx.send(
            f"Successfully converted {str(counter)} Level {str(level)} {animal}s into {int(counter / 2)} Level {str(level+1)} {animal}{'s' if amount != 1 else ''}{sending}"
        )
        if recreate:
            multiplier = await self.conf.user(ctx.author).multiplier()
            new = (
                "**Report:**\n"
                f"**To:** {ctx.author.display_name}\n"
                f"**Concerning:** Animal experiment #{str(math.ceil(((multiplier - 1) * 5) + 1))}\n"
                f"**Subject:** Animal experiment concluded.\n\n"
                f"Congratulations, {ctx.author.display_name}!  You have successfully combined enough animals to reach a Level 26 Animal!  This means that it is time to recreate universe!  This will give you a boost of 50,000 credits, remove all of your animals, and give you an extra 0.2% income rate for the next universe from all income.  Congratulations!\n\n"
                f"From, The Head {animal.title()}"
            )
            await ctx.send(new)
            await bank.deposit_credits(ctx.author, 50000)
            await self.conf.user(ctx.author).animals.set({1: 1})
            await self.conf.user(ctx.author).multiplier.set(multiplier + 0.2)
