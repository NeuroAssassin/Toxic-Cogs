# Pieces of this are taken from flare's pokecord cog

import asyncio
import contextlib
from typing import Any, Dict, Iterable, Optional

import discord
from aiohttp.web_request import Request
from redbot.core import commands
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
from redbot.vendored.discord.ext import menus


class ClientMenu(menus.MenuPages, inherit_buttons=False):
    def __init__(
        self,
        source: menus.PageSource,
        cog: Optional[commands.Cog] = None,
        ctx=None,
        user=None,
        clear_reactions_after: bool = True,
        delete_message_after: bool = True,
        add_reactions: bool = True,
        using_custom_emoji: bool = False,
        using_embeds: bool = False,
        keyword_to_reaction_mapping: Dict[str, str] = None,
        timeout: int = 180,
        message: discord.Message = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            source,
            clear_reactions_after=clear_reactions_after,
            delete_message_after=delete_message_after,
            check_embeds=using_embeds,
            timeout=timeout,
            message=message,
            **kwargs,
        )

    def reaction_check(self, payload):
        """The function that is used to check whether the payload should be processed.
        This is passed to :meth:`discord.ext.commands.Bot.wait_for <Bot.wait_for>`.

        There should be no reason to override this function for most users.

        Parameters
        ------------
        payload: :class:`discord.RawReactionActionEvent`
            The payload to check.

        Returns
        ---------
        :class:`bool`
            Whether the payload should be processed.
        """
        if payload.message_id != self.message.id:
            return False
        if payload.user_id not in (*self.bot.owner_ids, self._author_id):
            return False

        return payload.emoji in self.buttons

    @menus.button("\N{BLACK LEFT-POINTING TRIANGLE}", position=menus.First(0))
    async def prev(self, payload: discord.RawReactionActionEvent):
        if self.current_page == 0:
            await self.show_page(self._source.get_max_pages() - 1)
        else:
            await self.show_checked_page(self.current_page - 1)

    @menus.button("\N{CROSS MARK}", position=menus.First(1))
    async def stop_pages_default(self, payload: discord.RawReactionActionEvent) -> None:
        self.stop()

    @menus.button("\N{BLACK RIGHT-POINTING TRIANGLE}", position=menus.First(2))
    async def next(self, payload: discord.RawReactionActionEvent):
        if self.current_page == self._source.get_max_pages() - 1:
            await self.show_page(0)
        else:
            await self.show_checked_page(self.current_page + 1)

    @menus.button("\N{WARNING SIGN}\N{VARIATION SELECTOR-16}", position=menus.First(3))
    async def close_ws(self, payload: discord.RawReactionActionEvent):
        number = self.current_page
        msg = await self.ctx.send(
            (
                f"Are you sure you want to close RPC Client {number + 1}?  "
                "This will prevent them from communicating and may raise errors if not handled properly."
            )
        )
        emojis = ReactionPredicate.YES_OR_NO_EMOJIS
        start_adding_reactions(msg, emojis)
        pred = ReactionPredicate.yes_or_no(msg, self.ctx.author)
        with contextlib.suppress(asyncio.TimeoutError):
            await self.ctx.bot.wait_for("reaction_add", check=pred, timeout=30)

        if pred.result:
            # Definitely do NOT do this at home
            self.ctx.bot.rpc._rpc.clients[number].ws._reader.set_exception(Exception)
            await self.ctx.send(f"Successfully closed RPC Client {number + 1}")
        else:
            await self.ctx.send("Cancelled.")


class ClientList(menus.ListPageSource):
    def __init__(self, entries: Iterable[str]):
        super().__init__(entries, per_page=1)

    async def format_page(self, menu: ClientMenu, client: Request):
        description = (
            f"Connected to    [{client.url}]\n"
            f"Connected from  [{client.remote}]\n"
            f"Connected since [{client.ws._headers['Date']}]"
        )
        e = discord.Embed(
            title=f"RPC Client {menu.current_page + 1}/{self._max_pages}",
            description=box(description, lang="ini"),
            color=await menu.ctx.embed_color(),
        )
        return e

    def is_paginating(self):
        return True  # So it always adds reactions
