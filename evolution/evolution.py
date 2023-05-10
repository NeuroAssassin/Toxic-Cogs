"""
MIT License

Copyright (c) 2018-Present NeuroAssassin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import copy
import math
import random
import traceback
from collections import defaultdict
from datetime import timedelta
from typing import Literal, Optional

import discord
from redbot.core import Config, commands, errors
from redbot.core.bot import Red
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, humanize_number, humanize_timedelta, inline
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

from tabulate import tabulate

from .tasks import EvolutionTaskManager
from .utils import EvolutionUtils

from . import bank

ANIMALS = ["chicken", "dog", "cat", "shark", "tiger", "penguin", "pupper", "dragon"]

IMAGES = {
    "shark": "https://www.bostonmagazine.com/wp-content/uploads/sites/2/2019/05/Great-white-shark.jpg",
    "chicken": "https://i1.wp.com/thechickhatchery.com/wp-content/uploads/2018/01/RI-White.jpg?fit=371%2C363&ssl=1",
    "penguin": "https://cdn.britannica.com/77/81277-050-2A6A35B2/Adelie-penguin.jpg",
    "dragon": "https://images-na.ssl-images-amazon.com/images/I/61NTUxEnn0L._SL1032_.jpg",
    "tiger": "https://c402277.ssl.cf1.rackcdn.com/photos/18134/images/hero_small/Medium_WW226365.jpg?1574452099",
    "cat": "https://icatcare.org/app/uploads/2018/07/Thinking-of-getting-a-cat.png",
    "dog": "https://d17fnq9dkz9hgj.cloudfront.net/breed-uploads/2018/09/dog-landing-hero-lg.jpg?bust=1536935129&width=1080",
    "pupper": "https://i.ytimg.com/vi/MPV2METPeJU/maxresdefault.jpg",
}

import inspect


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

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        """This cog stores game data by user ID.  It will delete the user's game data,
        reset their progress and wipe traces of their ID."""
        await self.conf.user_from_id(user_id).clear()

        try:
            del self.cache[user_id]
        except KeyError:
            pass

        return

    @commands.group(aliases=["e", "evo"])
    async def evolution(self, ctx):
        """EVOLVE THE GREATEST ANIMALS OF ALL TIME!!!!"""
        pass

    @evolution.command(usage=" ")
    async def deletemydata(self, ctx, check: bool = False):
        """Delete your game data.

        WARNING!  Your data *will not be able to be recovered*!"""
        if not check:
            return await ctx.send(
                f"Warning!  This will completely delete your game data and restart you from scratch!  If you are sure you want to do this, re-run this command as `{ctx.prefix}evolution deletemydata True`."
            )
        await self.red_delete_data_for_user(requester="user", user_id=ctx.author.id)
        await ctx.send("Data deleted.  Your game data has been reset.")

    @commands.is_owner()
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

    @commands.is_owner()
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

    @evolution.group()
    async def market(self, ctx):
        """Buy or sell animals from different sellers"""
        pass

    @market.command(aliases=["shop"])
    async def store(
        self,
        ctx,
        level: Optional[int] = None,
        amount: Optional[int] = 1,
        skip_confirmation: Optional[bool] = False,
    ):
        """Buy animals from the always in-stock store.

        While the store will always have animals for sale, you cannot buy above a certain level,
        and they will be for a higher price."""
        if level is None:
            if ctx.channel.permissions_for(ctx.guild.me).embed_links:
                return await self.shop(ctx)
            else:
                return await ctx.send(
                    'I require the "Embed Links" permission to display the shop.'
                )
        if ctx.author.id in self.inmarket:
            return await ctx.send("Complete your current transaction or evolution first.")
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
        if level > 22:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send("The highest level you can buy is level 22.")

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
            box(
                f"[Transaction Complete]\nYou spent {humanize_number(price)} credits to buy {amount} Level {str(level)} {animal}{'s' if amount != 1 else ''}.",
                "css",
            )
        )
        self.inmarket.remove(ctx.author.id)

    async def shop(self, ctx, start_level: int = None):
        """Friendlier menu for displaying the animals available at the store."""
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
        if start_level and not (animals.get(str(start_level), False) is False):
            highest_level = start_level

        highest_level -= 1

        if highest_level < 0:
            highest_level = 0

        controls = dict(DEFAULT_CONTROLS)
        controls["\N{MONEY BAG}"] = self.utils.shop_control_callback
        await menu(ctx, embed_list, controls, page=highest_level)

    @market.command()
    async def daily(self, ctx):
        """View the daily deals.

        These will come at a lower price than the store, but can only be bought once per day.

        Status guide:
            A: Available to be bought and put in backyard
            B: Already purchased
            S: Available to be bought, but will be put in stash because you either do not have the space for the, or above your level threshold"""
        async with self.lock:
            data = await self.conf.user(ctx.author).all()
        animals = data["animals"]
        animal = data["animal"]

        if animal in ["", "P"]:
            return await ctx.send("Finish starting your evolution first")

        multiplier = data["multiplier"]
        highest = max(list(map(int, animals.keys())))
        e = 6 + math.ceil((multiplier - 1) * 5)

        display = []
        deals = await self.conf.daily()
        for did, deal in deals.items():
            status = ""
            amount = deal["details"]["amount"]
            level = deal["details"]["level"]
            if ctx.author.id in deal["bought"]:
                status = "[B]"
            elif (level > int(highest) - 3 and level != 1) or (
                amount + animals.get(str(level), 0) > e
            ):
                status = "#S "
            else:
                status = " A "

            price = self.utils.get_total_price(level, 0, amount, False) * 0.75

            display.append(
                [
                    did,
                    status,
                    humanize_number(price),
                    f"{amount} Level {level} {animal}{'s' if amount != 1 else ''}",
                ]
            )

        message = await ctx.send(
            f"{box(tabulate(display, tablefmt='psql'), lang='css')}Would you like to buy any of these fine animals?  Click the corresponding reaction below."
        )
        emojis = ReactionPredicate.NUMBER_EMOJIS[1:7]
        start_adding_reactions(message, emojis)

        pred = ReactionPredicate.with_emojis(emojis, message, ctx.author)
        try:
            await self.bot.wait_for("reaction_add", check=pred, timeout=60.0)
        except asyncio.TimeoutError:
            return await ctx.send(
                "The vendor grew uncomfortable with you there, and told you to leave and come back later."
            )

        if ctx.author.id in self.inmarket:
            return await ctx.send("Complete your current transaction or evolution first.")
        self.inmarket.append(ctx.author.id)
        buying = pred.result + 1

        deal = deals[str(buying)]
        if ctx.author.id in deal["bought"]:  # ;no
            self.inmarket.remove(ctx.author.id)
            return await ctx.send(
                "You already bought this deal.  You cannot buy daily deals multiple times."
            )

        level = deal["details"]["level"]
        amount = deal["details"]["amount"]

        price = self.utils.get_total_price(level, 0, amount, False) * 0.75
        balance = await bank.get_balance(ctx.author)

        if balance < price:
            self.inmarket.remove(ctx.author.id)
            return await ctx.send(
                f"You need {humanize_number(price - balance)} more credits to buy that deal."
            )

        stashing = 0
        delivering = amount
        if level > int(highest) - 3 and level != 1:
            stashing = amount
            delivering = 0
        elif amount + animals.get(str(level), 0) > e:
            delivering = e - animals[str(level)]
            stashing = amount - delivering

        async with self.lock:
            async with self.conf.user(ctx.author).all() as data:
                data["animals"][str(level)] = animals.get(str(level), 0) + delivering

                if stashing:
                    current_stash = data["stash"]["animals"].get(str(level), 0)
                    data["stash"]["animals"][str(level)] = current_stash + stashing

                self.cache[ctx.author.id] = data
            async with self.conf.daily() as data:  # In case someone buys at the same time, we need to re-read the data
                data[str(buying)]["bought"].append(ctx.author.id)

        await bank.withdraw_credits(ctx.author, int(price))
        await ctx.send(
            box(
                (
                    f"[Transaction Complete]\nYou spent {humanize_number(price)} credits to buy {amount} Level {str(level)} {animal}{'s' if amount != 1 else ''}."
                    f"\n\n{delivering} have been added to your backyard, {stashing} have been sent to your stash."
                ),
                "css",
            )
        )
        self.inmarket.remove(ctx.author.id)

    @evolution.group()
    async def stash(self, ctx):
        """Where your special animals are put if you cannot hold them in your backyard"""
        if not ctx.invoked_subcommand:
            await ctx.invoke(self.view)

    @stash.command()
    async def view(self, ctx):
        """View the animals and perks you have in your stash"""
        async with self.lock:
            data = await self.conf.user(ctx.author).all()

        animal = data["animal"]

        if animal in ["", "P"]:
            return await ctx.send("Finish starting your evolution first")

        if await ctx.embed_requested():
            embed = discord.Embed(
                title=f"{ctx.author.display_name}'s stash",
                description=(
                    "Animals/perks in your stash have no impact on you.  "
                    "They are here because you could not hold them at the time you picked up the items, or required approval."
                ),
                color=0xD2B48C,
            )
            asv = ""
            if not data["stash"]["animals"]:
                asv = inline("You do not have any animals in your stash.")
            else:
                for level, amount in data["stash"]["animals"].items():
                    asv += f"{humanize_number(amount)} Level {level} animal{'s' if amount != 1 else ''}\n"
            embed.add_field(name="Animal Stash", value=asv)

            psv = ""
            if not data["stash"]["perks"]:
                psv = inline("You do not have any perks in your stash.")
            else:
                pass
                # for level, amount in data["stash"]["perks"].items():
                #     asv += f"{humanize_number(amount)} Level {level} animal{'s' if amount != 1 else ''}\n"
            embed.add_field(name="Perk Stash", value=psv)

            await ctx.send(embed=embed)

    @stash.group()
    async def claim(self, ctx):
        """Claim animals or perks from your stash."""

    @claim.command()
    async def animal(self, ctx, level: int):
        """Claim animals from your stash"""
        async with self.lock:
            data = await self.conf.user(ctx.author).all()

        animal = data["animal"]

        if animal in ["", "P"]:
            return await ctx.send("Finish starting your evolution first")

        animals = data["animals"]
        stash = data["stash"]
        multiplier = data["multiplier"]
        highest = max(list(map(int, animals.keys())))
        e = 6 + math.ceil((multiplier - 1) * 5)

        try:
            level = int(level)
        except ValueError:
            return await ctx.send("Invalid level; please supply a number.")

        if level > 25 or level < 1:
            return await ctx.send("Invalid level; level cannot be above 25 or below 1.")

        try:
            amount = stash["animals"][str(level)]
            assert amount != 0
        except (KeyError, AssertionError):
            return await ctx.send("You don't have any animals at that level in your stash.")

        if level > int(highest) - 3 and level != 1:
            return await ctx.send(
                "You are not of a required level to claim those animals from stash.  Cancelled."
            )

        if animals.get(str(level), 0) == e:
            return await ctx.send(
                f"You already have the max amount of Level {level} animals in your backyard.  Cancelled."
            )

        async with self.lock:
            async with self.conf.user(ctx.author).all() as new_data:
                current = new_data["animals"].get(str(level), 0)
                amount = new_data["stash"]["animals"][str(level)]
                claiming = min([e - current, amount])

                full = True
                if claiming != amount:
                    full = False

                new_data["animals"][str(level)] = current + claiming
                if amount - claiming == 0:
                    del new_data["stash"]["animals"][str(level)]
                else:
                    new_data["stash"]["animals"][str(level)] = amount - claiming

                self.cache[ctx.author.id] = new_data
        extra = ""
        if not full:
            extra = f"There are still {amount - claiming} {animal}{'s' if claiming != 1 else ''} left in your Level {level} stash."
        await ctx.send(
            f"Successfully moved {claiming} {animal}{'s' if claiming != 1 else ''} from your stash to your backyard.  {extra}"
        )

    @claim.command(hidden=True)
    async def perk(self, ctx, *, name: str):
        """Claim a perk from your stash"""
        return await ctx.send("This command is not available.  Check back soon!")

    @commands.bot_has_permissions(embed_links=True)
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
            animals = {k: v for k, v in sorted(animals.items(), key=lambda x: int(x[0]))}
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
            return await ctx.send("Complete your current transaction or evolution first.")
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

        if level < 11:
            number = random.randint(1, 100)
        elif level < 21:
            number = random.randint(1, 1000)
        else:
            number = random.randint(1, 10000)
        if number == 1:
            # Evolution is going to fail
            number = random.randint(1, 10)
            extra = f"Your {animal}s were successfully recovered however."
            if number != 1:
                animals[currentlevelstr] -= 2 * amount
                extra = f"Your {animal}s were unable to be recovered."
            await ctx.send(
                box(
                    (
                        f"Evolution [Failed]\n\nFailed to convert {str(amount * 2)} Level {currentlevelstr} {animal}s "
                        f"into {str(amount)} Level {nextlevelstr} {animal}{'s'if amount != 1 else ''}.  {extra}"
                    ),
                    lang="css",
                )
            )
        else:
            animals[currentlevelstr] -= 2 * amount
            if highest == level:
                found_new = True
            animals[nextlevelstr] = animals.get(nextlevelstr, 0) + amount
            if level + 1 == 26:
                recreate = True

            if found_new:
                sending = "CONGRATULATIONS!  You have found a new animal!"
            else:
                sending = ""
            await ctx.send(
                box(
                    (
                        f"Evolution #Successful\n\nSuccessfully converted {str(amount * 2)} Level {currentlevelstr} {animal}s "
                        f"into {str(amount)} Level {nextlevelstr} {animal}{'s' if amount != 1 else ''}.\n\n{sending}"
                    ),
                    lang="css",
                )
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
                f"Congratulations, {ctx.author.display_name}!  You have successfully combined enough animals to reach a Level 26 Animal!  This means that it is time to recreate universe!  This will reset your bank account, remove all of your animals, but allow one more animal of every level, and give you an extra 20% income rate for the next universe from all income.  Congratulations!\n\n"
                f"From, The Head {animal.title()}"
            )
            await ctx.send(new)
            await bank.set_balance(ctx.author, 0)
        else:
            async with self.lock:
                await self.conf.user(ctx.author).animals.set(animals)
        self.inmarket.remove(ctx.author.id)
