import functools
from inspect import signature
from typing import List


def rpccheck():
    def conditional(func):
        @functools.wraps(func)
        async def rpccheckwrapped(self, *args, **kwargs):
            if self.bot.get_cog("Dashboard") and self.bot.is_ready():
                return await func(self, *args, **kwargs)
            else:
                return {"disconnected": True}

        rpccheckwrapped.__signature__ = signature(
            func
        )  # Because aiohttp json rpc doesn't accept *args, **kwargs
        return rpccheckwrapped

    return conditional


def permcheck(cog: str = None, permissions: List[str] = ["view"]):
    def conditional(func):
        @functools.wraps(func)
        async def permcheckwrapped(self, guild: int, member: int, *args, **kwargs):
            if cog:
                if not (self.bot.get_cog(cog)):
                    return {"status": 0, "message": f"The {cog} cog is not loaded"}
            if not (guildobj := self.bot.get_guild(int(guild))):
                return {"status": 0, "message": "Unknown guild"}

            m = guildobj.get_member(int(member))
            if not m:
                return {"status": 0, "message": "Unknown guild"}

            perms = self.cog.rpc.get_perms(guild, m)
            if perms is None:
                return {"status": 0, "message": "Unknown guild"}
            if int(member) != guildobj.owner_id:
                for perm in permissions:
                    if perm not in perms:
                        return {"status": 0, "message": "Unknown guild"}

            return await func(self, guildobj, m, *args, **kwargs)

        permcheckwrapped.__signature__ = signature(func)
        return permcheckwrapped

    return conditional


class FakePermissionsContext:
    """A fake context class so that the CogOrCommand class can be used"""

    def __init__(self, bot, guild):
        self.bot = bot
        self.guild = guild
