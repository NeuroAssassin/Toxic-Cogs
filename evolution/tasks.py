from __future__ import annotations

import asyncio
import contextlib
import random
import time
from typing import TYPE_CHECKING, Dict

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.utils import AsyncIter

if TYPE_CHECKING:
    from .evolution import Evolution

from . import bank


class EvolutionTaskManager:
    def __init__(self, cog):
        self.bot: Red = cog.bot
        self.conf: Config = cog.conf
        self.cog: Evolution = cog

        self.tasks: Dict[str, asyncio.Task] = {}

    async def process_credits(self, data, ct, timedata):
        all_gaining = 0
        async for key, value in AsyncIter(data.items()):
            last_processed = timedata[str(key)]
            if ct > last_processed + self.cog.utils.delays[int(key)]:
                for x in range(0, value):
                    chance = random.randint(1, 100)
                    chances = list(self.cog.utils.levels[int(key)].keys())
                    chosen = min([c for c in chances if chance <= c])
                    gaining = self.cog.utils.levels[int(key)][chosen]
                    all_gaining += gaining
        return all_gaining

    async def process_times(self, ct, timedata):
        async for key in AsyncIter(range(1, 26)):
            last_processed = timedata[str(key)]
            if ct > last_processed + self.cog.utils.delays[int(key)]:
                timedata[str(key)] = ct
        return timedata

    async def income_task(self):
        await self.bot.wait_until_ready()
        while True:
            # First, process the credits being added
            bulk_edit = {}
            ct = time.time()
            lastcredited = await self.cog.conf.lastcredited()
            async for userid, data in AsyncIter(self.cog.cache.copy().items()):
                animal = data["animal"]
                if animal == "":
                    continue
                multiplier = data["multiplier"]
                animals = data["animals"]
                gaining = await self.process_credits(animals, ct, lastcredited) * multiplier
                bulk_edit[str(userid)] = gaining

            # Credit to aikaterna's seen cog for this bulk write
            config = bank._get_config()
            users = config._get_base_group(config.USER)
            max_credits = await bank.get_max_balance()
            async with users.all() as new_data:
                for user_id, userdata in bulk_edit.items():
                    if str(user_id) not in new_data:
                        new_data[str(user_id)] = {"balance": userdata}
                        continue
                    if new_data[str(user_id)]["balance"] + userdata > max_credits:
                        new_data[str(user_id)]["balance"] = int(max_credits)
                    else:
                        new_data[str(user_id)]["balance"] = int(
                            new_data[str(user_id)]["balance"] + userdata
                        )

            await self.cog.conf.lastcredited.set(await self.process_times(ct, lastcredited))
            await asyncio.sleep(60)

    async def daily_task(self):
        await self.bot.wait_until_ready()
        while True:
            lastdailyupdate = await self.cog.conf.lastdailyupdate()
            if lastdailyupdate + 86400 <= time.time():
                deals = {}
                levels = random.sample(
                    self.cog.utils.randlvl_chances, len(self.cog.utils.randlvl_chances)
                )
                amounts = random.sample(
                    self.cog.utils.randamt_chances, len(self.cog.utils.randamt_chances)
                )
                for x in range(1, 7):
                    level = random.choice(levels)
                    amount = random.choice(amounts)
                    deals[str(x)] = {"details": {"level": level, "amount": amount}, "bought": []}
                await self.cog.conf.daily.set(deals)
                await self.cog.conf.lastdailyupdate.set(time.time())
            await asyncio.sleep(300)

    def get_statuses(self):
        returning = {}
        for task, obj in self.tasks.items():
            exc = None
            with contextlib.suppress(asyncio.exceptions.InvalidStateError):
                exc = obj.exception()
            returning[task] = {"state": obj._state, "exc": exc}
        return returning

    def init_tasks(self):
        self.tasks["income"] = self.bot.loop.create_task(self.income_task())
        self.tasks["daily"] = self.bot.loop.create_task(self.daily_task())

    def shutdown(self):
        for task in self.tasks.values():
            task.cancel()
