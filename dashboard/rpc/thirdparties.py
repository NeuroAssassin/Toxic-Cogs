from redbot.core.bot import Red
from redbot.core.commands import commands

import discord
import inspect
import typing

from .utils import rpccheck


def dashboard_page(name: typing.Optional[str] = None, methods: typing.List[str] = ["GET"], context_ids: typing.List[str] = None, required_kwargs: typing.List[str] = None, permissions_required: typing.List[str] = ["view"], hidden: typing.Optional[bool] = None):
    if context_ids is None:
        context_ids = []
    if required_kwargs is None:
        required_kwargs = []

    def decorator(func: typing.Callable):
        if name is not None and not isinstance(name, str):
            raise TypeError("Name of a page must be a string.")
        if name is not None:
            discord.app_commands.commands.validate_name(name)
        if not inspect.iscoroutinefunction(func):
            raise TypeError("Func must be a coroutine.")
        params = {"name": name, "methods": methods, "context_ids": context_ids, "required_kwargs": required_kwargs, "permissions_required": permissions_required, "hidden": hidden, "real_cog_name": None}
        for key, value in inspect.signature(func).parameters.items():
            if value.name == "self" or value.kind in [inspect._ParameterKind.POSITIONAL_ONLY, inspect._ParameterKind.VAR_KEYWORD]:
                continue
            if value.default is not inspect._empty:
                continue
            if key in ["user_id", "guild_id", "member_id", "role_id", "channel_id"] and key not in params["context_ids"]:
                params["context_ids"].append(key)
            elif f"{key}_id" in ["user_id", "guild_id", "member_id", "role_id", "channel_id"] and f"{key}_id" not in params["context_ids"]:
                params["context_ids"].append(f"{key}_id")
            elif key not in ["method", "lang_code"]:
                params["required_kwargs"].append(key)
        # A guild must be chose for these kwargs.
        for key in ["member_id", "role_id", "channel_id"]:
            if key in params["context_ids"] and "guild_id" not in params["context_ids"]:
                params["context_ids"].append("guild_id")
        # No guild available without user connection.
        if (
            "guild_id" in params["context_ids"]
            and "user_id" not in params["context_ids"]
        ):
            params["context_ids"].append("user_id")
        if params["hidden"] is None:
            params["hidden"] = params["required_kwargs"] or [x for x in params["context_ids"] if x not in ["user_id", "guild_id"]]
        func.__dashboard_params__ = params.copy()
        return func

    return decorator


class DashboardRPC_ThirdParties:
    def __init__(self, cog: commands.Cog):
        self.bot: Red = cog.bot
        self.cog: commands.Cog = cog

        self.third_parties: typing.Dict[str, typing.Dict[str, typing.Tuple[typing.Callable, typing.Dict[str, bool]]]] = {}
        self.third_parties_cogs: typing.Dict[str, commands.Cog] = {}

        self.bot.register_rpc_handler(self.data_receive)
        self.bot.add_listener(self.on_cog_add)
        self.bot.add_listener(self.on_cog_remove)
        self.bot.dispatch("dashboard_cog_add", self.cog)

    def unload(self):
        self.bot.unregister_rpc_handler(self.data_receive)
        self.bot.remove_listener(self.on_cog_add)
        self.bot.remove_listener(self.on_cog_remove)

    @commands.Cog.listener()
    async def on_cog_add(self, cog: commands.Cog):
        ev = "on_dashboard_cog_add"
        funcs = [listener[1] for listener in cog.get_listeners() if listener[0] == ev]
        for func in funcs:
            self.bot._schedule_event(func, ev, self.cog)  # like in `bot.dispatch`

    @commands.Cog.listener()
    async def on_cog_remove(self, cog: commands.Cog):
        if cog not in self.third_parties_cogs.values():
            return
        self.remove_third_party(cog)

    def add_third_party(self, cog: commands.Cog, overwrite: bool = False):
        cog_name = cog.qualified_name.lower()
        if cog_name in self.third_parties and not overwrite:
            raise RuntimeError(f"The cog {cog_name} is already an existing third party.")
        _pages = {}
        for attr in dir(cog):
            if hasattr((func := getattr(cog, attr)), "__dashboard_params__"):
                page = func.__dashboard_params__["name"]
                if page in _pages:
                    raise RuntimeError(f"The page {page} is already an existing page for this third party.")
                func.__dashboard_params__["real_cog_name"] = cog.qualified_name
                _pages[page] = (func, func.__dashboard_params__)
        if not _pages:
            raise RuntimeError("No page found.")
        self.third_parties[cog_name] = _pages
        self.third_parties_cogs[cog_name] = cog

    def remove_third_party(self, cog: commands.Cog):
        cog_name = cog.qualified_name.lower()
        try:
            del self.third_parties_cogs[cog_name]
        except KeyError:
            pass
        return self.third_parties.pop(cog_name, None)

    @rpccheck()
    async def get_third_parties(self):
        return {key: {k: v[1] for k, v in value.items()} for key, value in self.third_parties.items()}

    @rpccheck()
    async def data_receive(self, method: str, cog_name: str, page: str, context_ids: typing.Optional[typing.Dict[str, int]] = None, kwargs: typing.Dict[str, typing.Any] = None, lang_code: typing.Optional[str] = None) -> typing.Dict[str, typing.Any]:
        if context_ids is None:
            context_ids = {}
        if kwargs is None:
            kwargs = {}
        cog_name = cog_name.lower()
        if not cog_name or cog_name not in self.third_parties or cog_name not in self.third_parties_cogs:
            return {"status": 1, "message": "Third party not found.", "error_message": "404: Looks like that third party doesn't exist... Strange..."}
        if self.bot.get_cog(self.third_parties_cogs[cog_name].qualified_name) is None:
            return {"status": 1, "message": "Third party not loaded.", "error_message": "404: Looks like that third party doesn't exist... Strange..."}
        page = page.lower() if page is not None else page
        if page not in self.third_parties[cog_name]:
            return {"status": 1, "message": "Page not found.", "error_message": "404: Looks like that page doesn't exist... Strange..."}
        kwargs["method"] = method
        if "user_id" in self.third_parties[cog_name][page][1]["context_ids"]:
            if (user := self.bot.get_user(context_ids["user_id"])) is None:
                return {"status": 1, "message": "Page not found.", "error_message": "404: Looks like that I do not share any server with you..."}
            kwargs["user_id"] = context_ids["user_id"]
            kwargs["user"] = user
        if "guild_id" in self.third_parties[cog_name][page][1]["context_ids"] and "user_id" in self.third_parties[cog_name][page][1]["context_ids"]:
            if (guild := self.bot.get_guild(context_ids["guild_id"])) is None:
                return {"status": 1, "message": "Page not found.", "error_message": "404: Looks like that I'm not in this server..."}
            if (m := guild.get_member(context_ids["user_id"])) is None:
                return {"status": 1, "message": "Page not found.", "error_message": "403: Looks like that you're not in this server..."}
            if m.id != guild.owner.id:
                perms = self.cog.rpc.get_perms(guildid=guild.id, m=m)
                if perms is None:
                    return {"status": 1, "message": "Page not found.", "error_message": "403: Looks like that you haven't permissions in this server..."}
                for permission in self.third_parties[cog_name][page][1]["permissions_required"]:
                    if permission not in perms:
                        return {"status": 1, "message": "Page not found.", "error_message": "403: Looks like that you haven't permissions in this server..."}
            kwargs["guild_id"] = context_ids["guild_id"]
            kwargs["guild"] = guild
            if "member_id" in self.third_parties[cog_name][page][1]["context_ids"]:
                if (member := guild.get_member(context_ids["member_id"])) is None:
                    return {"status": 1, "message": "Page not found.", "error_message": "404: Looks like that this member is not found in this guild..."}
                kwargs["member_id"] = context_ids["member_id"]
                kwargs["member"] = member
            if "role_id" in self.third_parties[cog_name][page][1]["context_ids"]:
                if (role := guild.get_role(context_ids["role_id"])) is None:
                    return {"status": 1, "message": "Page not found.", "error_message": "404: Looks like that this role is not found in this guild..."}
                kwargs["role_id"] = context_ids["role_id"]
                kwargs["role"] = role
            if "channel_id" in self.third_parties[cog_name][page][1]["context_ids"]:
                if (channel := guild.get_channel(context_ids["channel_id"])) is None:
                    return {"status": 1, "message": "Page not found.", "error_message": "404: Looks like that this channel is not found in this guild..."}
                kwargs["channel_id"] = context_ids["channel_id"]
                kwargs["channel"] = channel
        kwargs["lang_code"] = lang_code or "en-EN"
        return await self.third_parties[cog_name][page][0](**kwargs)
