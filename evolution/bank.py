from __future__ import annotations

import asyncio
import datetime
from functools import wraps
from typing import TYPE_CHECKING, List, Optional, Union

import discord
from redbot.core import Config, bank, commands, errors
from redbot.core.bank import Account
from redbot.core.bank import BankPruneError as BankPruneError
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_number

if TYPE_CHECKING:
    from redbot.core.bot import Red

# Credits: https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/core/bank.py
# This is a modified version of Red's Bank API that listen for the existance of the Adventure Cog.
# If Cog is not loaded, then it will default to Red's Bank API

_ = Translator("Adventure Bank API", __file__)

__all__ = [
    "Account",
    "get_balance",
    "set_balance",
    "withdraw_credits",
    "deposit_credits",
    "can_spend",
    "transfer_credits",
    "wipe_bank",
    "get_account",
    "is_global",
    "set_global",
    "get_bank_name",
    "set_bank_name",
    "get_currency_name",
    "set_currency_name",
    "get_default_balance",
    "set_default_balance",
    "get_max_balance",
    "set_max_balance",
    "cost",
    "AbortPurchase",
    "bank_prune",
    "get_next_payday",
    "set_next_payday",
    "BankPruneError",
]

_MAX_BALANCE = 2 ** 63 - 1

_DEFAULT_MEMBER = {"balance": 0, "next_payday": 0}


_config: Config = None
_bot: Red = None


def _init(bot: Red):
    global _config, _bot
    if _config is None:
        _config = Config.get_conf(
            None, 384734293238749, cog_name="AdventureBank", force_registration=True
        )
        _config.register_user(**_DEFAULT_MEMBER)
    _bot = bot


class AdventureAccount:
    """A single account.
    This class should ONLY be instantiated by the bank itself."""

    def __init__(self, balance: int, next_payday: int):
        self.balance = balance
        self.next_payday = next_payday


def _encoded_current_time() -> int:
    """Get the current UTC time as a timestamp.

    Returns
    -------
    int
        The current UTC timestamp.
    """
    now = datetime.datetime.utcnow()
    return _encode_time(now)


def _encode_time(time: datetime.datetime) -> int:
    """Convert a datetime object to a serializable int.

    Parameters
    ----------
    time : datetime.datetime
        The datetime to convert.

    Returns
    -------
    int
        The timestamp of the datetime object.
    """
    ret = int(time.timestamp())
    return ret


def _decode_time(time: int) -> datetime.datetime:
    """Convert a timestamp to a datetime object.

    Parameters
    ----------
    time : int
        The timestamp to decode.

    Returns
    -------
    datetime.datetime
        The datetime object from the timestamp.
    """
    return datetime.datetime.utcfromtimestamp(time)


async def get_balance(member: discord.Member, _forced: bool = False) -> int:
    """Get the current balance of a member.
    Parameters
    ----------
    member : discord.Member
        The member whose balance to check.
    Returns
    -------
    int
        The member's balance
    """
    acc = await get_account(member, _forced=_forced)
    return int(acc.balance)


async def get_next_payday(member: discord.Member) -> int:
    """Get the current balance of a member.
    Parameters
    ----------
    member : discord.Member
        The member whose balance to check.
    Returns
    -------
    int
        The member's balance
    """
    if (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return 0

    acc = await get_account(member)
    return int(acc.next_payday)


async def set_next_payday(member: Union[discord.Member, discord.User], amount: int) -> int:
    """Set an account next payday.
    Parameters
    ----------
    member : Union[discord.Member, discord.User]
        The member whose next payday to set.
    amount : int
        The amount to set the next payday to.
    Returns
    -------
    int
        New account next payday.
    """
    if (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return 0
    amount = int(amount)
    group = _config.user(member)
    await group.next_payday.set(amount)
    return amount


async def can_spend(member: discord.Member, amount: int, _forced: bool = False) -> bool:
    """Determine if a member can spend the given amount.
    Parameters
    ----------
    member : discord.Member
        The member wanting to spend.
    amount : int
        The amount the member wants to spend.
    Returns
    -------
    bool
        :code:`True` if the member has a sufficient balance to spend the
        amount, else :code:`False`.
    """
    return await get_balance(member, _forced=_forced) >= amount


async def set_balance(
    member: Union[discord.Member, discord.User], amount: int, _forced: bool = False
) -> int:
    """Set an account balance.
    Parameters
    ----------
    member : Union[discord.Member, discord.User]
        The member whose balance to set.
    amount : int
        The amount to set the balance to.
    Returns
    -------
    int
        New account balance.
    Raises
    ------
    ValueError
        If attempting to set the balance to a negative number.
    RuntimeError
        If the bank is guild-specific and a discord.User object is provided.
    BalanceTooHigh
        If attempting to set the balance to a value greater than
        ``bank._MAX_BALANCE``.
    """
    if _forced or (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return await bank.set_balance(member=member, amount=amount)

    guild = getattr(member, "guild", None)
    max_bal = await get_max_balance(guild)
    if amount > max_bal:
        currency = await get_currency_name(guild)
        raise errors.BalanceTooHigh(
            user=member.display_name, max_balance=max_bal, currency_name=currency
        )
    amount = int(amount)
    group = _config.user(member)
    await group.balance.set(amount)
    return amount


async def withdraw_credits(member: discord.Member, amount: int, _forced: bool = False) -> int:
    """Remove a certain amount of credits from an account.
    Parameters
    ----------
    member : discord.Member
        The member to withdraw credits from.
    amount : int
        The amount to withdraw.
    Returns
    -------
    int
        New account balance.
    Raises
    ------
    ValueError
        If the withdrawal amount is invalid or if the account has insufficient
        funds.
    TypeError
        If the withdrawal amount is not an `int`.
    """
    if _forced or (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return await bank.withdraw_credits(member=member, amount=amount)

    if not isinstance(amount, (int, float)):
        raise TypeError("Withdrawal amount must be of type int, not {}.".format(type(amount)))
    amount = int(amount)
    bal = await get_balance(member)
    if amount > bal:
        raise ValueError(
            "Insufficient funds {} > {}".format(
                humanize_number(amount, override_locale="en_US"),
                humanize_number(bal, override_locale="en_US"),
            )
        )

    return await set_balance(member, bal - amount)


async def deposit_credits(member: discord.Member, amount: int, _forced: bool = False) -> int:
    """Add a given amount of credits to an account.
    Parameters
    ----------
    member : discord.Member
        The member to deposit credits to.
    amount : int
        The amount to deposit.
    Returns
    -------
    int
        The new balance.
    Raises
    ------
    ValueError
        If the deposit amount is invalid.
    TypeError
        If the deposit amount is not an `int`.
    """
    if _forced or (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return await bank.deposit_credits(member=member, amount=amount)
    if not isinstance(amount, (int, float)):
        raise TypeError("Deposit amount must be of type int, not {}.".format(type(amount)))
    amount = int(amount)
    bal = int(await get_balance(member))
    return await set_balance(member, amount + bal)


async def transfer_credits(
    from_: Union[discord.Member, discord.User],
    to: Union[discord.Member, discord.User],
    amount: int,
    tax: float = 0.0,
):
    """Transfer a given amount of credits from one account to another with a 50% tax.
    Parameters
    ----------
    from_: Union[discord.Member, discord.User]
        The member to transfer from.
    to : Union[discord.Member, discord.User]
        The member to transfer to.
    amount : int
        The amount to transfer.
    Returns
    -------
    int
        The new balance of the member gaining credits.
    Raises
    ------
    ValueError
        If the amount is invalid or if ``from_`` has insufficient funds.
    TypeError
        If the amount is not an `int`.
    RuntimeError
        If the bank is guild-specific and a discord.User object is provided.
    BalanceTooHigh
        If the balance after the transfer would be greater than
        ``bank._MAX_BALANCE``.
    """
    if (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return await bank.transfer_credits(from_=from_, to=to, amount=amount)

    if not isinstance(amount, (int, float)):
        raise TypeError("Transfer amount must be of type int, not {}.".format(type(amount)))

    guild = getattr(to, "guild", None)
    max_bal = await get_max_balance(guild)
    new_amount = int(amount - (amount * tax))
    if await get_balance(to) + new_amount > max_bal:
        currency = await get_currency_name(guild)
        raise errors.BalanceTooHigh(
            user=to.display_name, max_balance=max_bal, currency_name=currency
        )

    await withdraw_credits(from_, int(amount))
    await deposit_credits(to, int(new_amount))
    return int(new_amount)


async def wipe_bank(guild: Optional[discord.Guild] = None) -> None:
    """Delete all accounts from the bank.
    Parameters
    ----------
    guild : discord.Guild
        The guild to clear accounts for. If unsupplied and the bank is
        per-server, all accounts in every guild will be wiped.
    """
    if (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return await bank.wipe_bank(guild=guild)
    await _config.clear_all_users()


async def bank_prune(bot: Red, guild: discord.Guild = None, user_id: int = None) -> None:
    """Prune bank accounts from the bank.
    Parameters
    ----------
    bot : Red
        The bot.
    guild : discord.Guild
        The guild to prune. This is required if the bank is set to local.
    user_id : int
        The id of the user whose account will be pruned.
        If supplied this will prune only this user's bank account
        otherwise it will prune all invalid users from the bank.
    Raises
    ------
    BankPruneError
        If guild is :code:`None` and the bank is Local.
    """
    if (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return await bank.bank_prune(bot=bot, guild=guild, user_id=user_id)

    _guilds = set()
    _uguilds = set()
    if user_id is None:
        async for g in AsyncIter(bot.guilds, steps=100):
            if not g.unavailable and g.large and not g.chunked:
                _guilds.add(g)
            elif g.unavailable:
                _uguilds.add(g)
    group = _config._get_base_group(_config.USER)

    if user_id is None:
        await bot.request_offline_members(*_guilds)
        accounts = await group.all()
        tmp = accounts.copy()
        members = bot.get_all_members()
        user_list = {str(m.id) for m in members if m.guild not in _uguilds}

    async with group.all() as bank_data:  # FIXME: use-config-bulk-update
        if user_id is None:
            for acc in tmp:
                if acc not in user_list:
                    del bank_data[acc]
        else:
            user_id = str(user_id)
            if user_id in bank_data:
                del bank_data[user_id]


async def get_leaderboard(
    positions: int = None, guild: discord.Guild = None, _forced: bool = False
) -> List[tuple]:
    """
    Gets the bank's leaderboard
    Parameters
    ----------
    positions : `int`
        The number of positions to get
    guild : discord.Guild
        The guild to get the leaderboard of. If the bank is global and this
        is provided, get only guild members on the leaderboard
    Returns
    -------
    `list` of `tuple`
        The sorted leaderboard in the form of :code:`(user_id, raw_account)`
    Raises
    ------
    TypeError
        If the bank is guild-specific and no guild was specified
    """
    if _forced or (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return await bank.get_leaderboard(positions=positions, guild=guild)
    raw_accounts = await _config.all_users()
    if guild is not None:
        tmp = raw_accounts.copy()
        for acc in tmp:
            if not guild.get_member(acc):
                del raw_accounts[acc]
    sorted_acc = sorted(raw_accounts.items(), key=lambda x: x[1]["balance"], reverse=True)
    if positions is None:
        return sorted_acc
    else:
        return sorted_acc[:positions]


async def get_leaderboard_position(
    member: Union[discord.User, discord.Member], _forced: bool = False
) -> Union[int, None]:
    """
    Get the leaderboard position for the specified user
    Parameters
    ----------
    member : `discord.User` or `discord.Member`
        The user to get the leaderboard position of
    Returns
    -------
    `int`
        The position of the user on the leaderboard
    Raises
    ------
    TypeError
        If the bank is currently guild-specific and a `discord.User` object was passed in
    """
    if await is_global():
        guild = None
    else:
        guild = member.guild if hasattr(member, "guild") else None
    try:
        leaderboard = await get_leaderboard(None, guild, _forced=_forced)
    except TypeError:
        raise
    else:
        pos = discord.utils.find(lambda x: x[1][0] == member.id, enumerate(leaderboard, 1))
        if pos is None:
            return None
        else:
            return pos[0]


async def get_account(
    member: Union[discord.Member, discord.User], _forced: bool = False
) -> Union[Account, AdventureAccount]:
    """Get the appropriate account for the given user or member.
    A member is required if the bank is currently guild specific.
    Parameters
    ----------
    member : `discord.User` or `discord.Member`
        The user whose account to get.
    Returns
    -------
    Account
        The user's account.
    """
    if _forced or (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return await bank.get_account(member)

    all_accounts = await _config.all_users()
    if member.id not in all_accounts:
        acc_data = {"balance": 250, "next_payday": 0}
    else:
        acc_data = all_accounts[member.id]
    return AdventureAccount(**acc_data)


async def is_global(_forced: bool = False) -> bool:
    """Determine if the bank is currently global.
    Returns
    -------
    bool
        :code:`True` if the bank is global, otherwise :code:`False`.
    """
    if _forced or (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return await bank.is_global()
    return True


async def set_global(global_: bool) -> bool:
    """Set global status of the bank.
    .. important::
        All accounts are reset when you switch!
    Parameters
    ----------
    global_ : bool
        :code:`True` will set bank to global mode.
    Returns
    -------
    bool
        New bank mode, :code:`True` is global.
    Raises
    ------
    RuntimeError
        If bank is becoming global and a `discord.Member` was not provided.
    """
    return await bank.set_global(global_)


async def get_bank_name(guild: discord.Guild = None) -> str:
    """Get the current bank name.
    Parameters
    ----------
    guild : `discord.Guild`, optional
        The guild to get the bank name for (required if bank is
        guild-specific).
    Returns
    -------
    str
        The bank's name.
    Raises
    ------
    RuntimeError
        If the bank is guild-specific and guild was not provided.
    """
    return await bank.get_bank_name(guild)


async def set_bank_name(name: str, guild: discord.Guild = None) -> str:
    """Set the bank name.
    Parameters
    ----------
    name : str
        The new name for the bank.
    guild : `discord.Guild`, optional
        The guild to set the bank name for (required if bank is
        guild-specific).
    Returns
    -------
    str
        The new name for the bank.
    Raises
    ------
    RuntimeError
        If the bank is guild-specific and guild was not provided.
    """
    return await bank.set_bank_name(name=name, guild=guild)


async def get_currency_name(guild: discord.Guild = None, _forced: bool = False) -> str:
    """Get the currency name of the bank.
    Parameters
    ----------
    guild : `discord.Guild`, optional
        The guild to get the currency name for (required if bank is
        guild-specific).
    Returns
    -------
    str
        The currency name.
    Raises
    ------
    RuntimeError
        If the bank is guild-specific and guild was not provided.
    """
    if _forced or (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return await bank.get_currency_name(guild=guild)
    return _("gold coins")


async def set_currency_name(name: str, guild: discord.Guild = None) -> str:
    """Set the currency name for the bank.
    Parameters
    ----------
    name : str
        The new name for the currency.
    guild : `discord.Guild`, optional
        The guild to set the currency name for (required if bank is
        guild-specific).
    Returns
    -------
    str
        The new name for the currency.
    Raises
    ------
    RuntimeError
        If the bank is guild-specific and guild was not provided.
    """
    return await bank.set_currency_name(name=name, guild=guild)


async def get_max_balance(guild: discord.Guild = None) -> int:
    """Get the max balance for the bank.
    Parameters
    ----------
    guild : `discord.Guild`, optional
        The guild to get the max balance for (required if bank is
        guild-specific).
    Returns
    -------
    int
        The maximum allowed balance.
    Raises
    ------
    RuntimeError
        If the bank is guild-specific and guild was not provided.
    """
    if (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return await bank.get_max_balance(guild=guild)
    return _MAX_BALANCE


async def set_max_balance(amount: int, guild: discord.Guild = None) -> int:
    """Set the maximum balance for the bank.
    Parameters
    ----------
    amount : int
        The new maximum balance.
    guild : `discord.Guild`, optional
        The guild to set the max balance for (required if bank is
        guild-specific).
    Returns
    -------
    int
        The new maximum balance.
    Raises
    ------
    RuntimeError
        If the bank is guild-specific and guild was not provided.
    ValueError
        If the amount is less than 0 or higher than 2 ** 63 - 1.
    """
    return await bank.set_max_balance(amount=amount, guild=guild)


async def get_default_balance(guild: discord.Guild = None) -> int:
    """Get the current default balance amount.
    Parameters
    ----------
    guild : `discord.Guild`, optional
        The guild to get the default balance for (required if bank is
        guild-specific).
    Returns
    -------
    int
        The bank's default balance.
    Raises
    ------
    RuntimeError
        If the bank is guild-specific and guild was not provided.
    """
    return await bank.get_default_balance(guild=guild)


async def set_default_balance(amount: int, guild: discord.Guild = None) -> int:
    """Set the default balance amount.
    Parameters
    ----------
    amount : int
        The new default balance.
    guild : `discord.Guild`, optional
        The guild to set the default balance for (required if bank is
        guild-specific).
    Returns
    -------
    int
        The new default balance.
    Raises
    ------
    RuntimeError
        If the bank is guild-specific and guild was not provided.
    ValueError
        If the amount is less than 0 or higher than the max allowed balance.
    """
    return await bank.set_default_balance(amount=amount, guild=guild)


class AbortPurchase(Exception):
    pass


def cost(amount: int):
    """
    Decorates a coroutine-function or command to have a cost.
    If the command raises an exception, the cost will be refunded.
    You can intentionally refund by raising `AbortPurchase`
    (this error will be consumed and not show to users)
    Other exceptions will propagate and will be handled by Red's (and/or
    any other configured) error handling.
    """
    if not isinstance(amount, int) or amount < 0:
        raise ValueError("This decorator requires an integer cost greater than or equal to zero")

    def deco(coro_or_command):
        is_command = isinstance(coro_or_command, commands.Command)
        if not is_command and not asyncio.iscoroutinefunction(coro_or_command):
            raise TypeError("@bank.cost() can only be used on commands or `async def` functions")

        coro = coro_or_command.callback if is_command else coro_or_command

        @wraps(coro)
        async def wrapped(*args, **kwargs):
            context: commands.Context = None
            for arg in args:
                if isinstance(arg, commands.Context):
                    context = arg
                    break

            if not context.guild and not await is_global():
                raise commands.UserFeedbackCheckFailure(
                    _("Can't pay for this command in DM without a global bank.")
                )
            try:
                await withdraw_credits(context.author, amount)
            except Exception:
                credits_name = await get_currency_name(context.guild)
                raise commands.UserFeedbackCheckFailure(
                    _("You need at least {cost} {currency} to use this command.").format(
                        cost=humanize_number(amount), currency=credits_name
                    )
                )
            else:
                try:
                    return await coro(*args, **kwargs)
                except AbortPurchase:
                    await deposit_credits(context.author, amount)
                except Exception:
                    await deposit_credits(context.author, amount)
                    raise

        if not is_command:
            return wrapped
        else:
            wrapped.__module__ = coro_or_command.callback.__module__
            coro_or_command.callback = wrapped
            return coro_or_command


def _get_config(_forced: bool = False):
    if _forced or (cog := _bot.get_cog("Adventure")) is None or not cog._separate_economy:
        return bank._config
    return _config
