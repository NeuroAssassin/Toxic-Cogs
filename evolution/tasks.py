from __future__ import annotations
from redbot.core.bot import Red
from redbot.core import Config, bank, errors
from redbot.core.utils import AsyncIter
from redbot.core.bank import _config as bank_config
from typing import Dict, TYPE_CHECKING
import asyncio
import random
import math
import contextlib
import time

if TYPE_CHECKING:
    from .evolution import Evolution


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

            # Credit to aikatern'a seen cog for this bulk write
            users = bank_config._get_base_group(bank_config.USER)
            async with users.all() as new_data:
                for user_id, userdata in bulk_edit.items():
                    if str(user_id) not in new_data:
                        new_data[str(user_id)] = {"name": "", "created_at": 0, "balance": userdata}
                        continue
                    new_data[str(user_id)]["balance"] += userdata

            await self.cog.conf.lastcredited.set(await self.process_times(ct, lastcredited))
            await asyncio.sleep(60)

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

    def shutdown(self):
        for task in self.tasks.values():
            task.cancel()
