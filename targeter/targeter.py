import argparse
import functools
import re
from datetime import datetime

import aiohttp
import discord
from redbot.core import checks, commands
from redbot.core.commands import BadArgument, Converter, RoleConverter
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

PERMS = [
    "add_reactions",
    "administrator",
    "attach_files",
    "ban_members",
    "change_nickname",
    "connect",
    "create_instant_invite",
    "deafen_members",
    "embed_links",
    "external_emojis",
    "kick_members",
    "manage_channels",
    "manage_emojis",
    "manage_guild",
    "manage_messages",
    "manage_nicknames",
    "manage_roles",
    "manage_webhooks",
    "mention_everyone",
    "move_members",
    "mute_members",
    "priority_speaker",
    "read_message_history",
    "read_messages",
    "send_messages",
    "send_tts_messages",
    "speak",
    "stream",
    "use_voice_activation",
    "view_audit_log",
]


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()


class Args(Converter):
    async def convert(self, ctx, argument):
        argument = argument.replace("—", "--")
        parser = NoExitParser(description="Targeter argument parser", add_help=False)

        # Nicknames / Usernames
        names = parser.add_mutually_exclusive_group()
        names.add_argument("--nick", nargs="*", dest="nick", default=[])
        names.add_argument("--user", nargs="*", dest="user", default=[])
        names.add_argument("--name", nargs="*", dest="name", default=[])

        names.add_argument("--not-nick", nargs="*", dest="not-nick", default=[])
        names.add_argument("--not-user", nargs="*", dest="not-user", default=[])
        names.add_argument("--not-name", nargs="*", dest="not-name", default=[])

        names.add_argument("--a-nick", dest="a-nick", action="store_true")
        names.add_argument("--no-nick", dest="no-nick", action="store_true")

        discs = parser.add_mutually_exclusive_group()
        discs.add_argument("--disc", nargs="*", dest="disc", default=[])
        discs.add_argument("--not-disc", nargs="*", dest="ndisc", default=[])

        # Roles
        parser.add_argument("--roles", nargs="*", dest="roles", default=[])
        parser.add_argument("--any-role", nargs="*", dest="any-role", default=[])

        parser.add_argument("--not-roles", nargs="*", dest="not-roles", default=[])
        parser.add_argument("--not-any-role", nargs="*", dest="not-any-role", default=[])

        single = parser.add_mutually_exclusive_group()
        single.add_argument("--a-role", dest="a-role", action="store_true")
        single.add_argument("--no-role", dest="no-role", action="store_true")

        # Date stuff
        jd = parser.add_mutually_exclusive_group()
        jd.add_argument("--joined-on", nargs="*", dest="joined-on", default=[])
        jd.add_argument("--joined-before", nargs="*", dest="joined-be", default=[])
        jd.add_argument("--joined-after", nargs="*", dest="joined-af", default=[])

        cd = parser.add_mutually_exclusive_group()
        cd.add_argument("--created-on", nargs="*", dest="created-on", default=[])
        cd.add_argument("--created-before", nargs="*", dest="created-be", default=[])
        cd.add_argument("--created-after", nargs="*", dest="created-af", default=[])

        # Status / Activity / Device / Just Basically Profile Stuff
        parser.add_argument("--status", nargs="*", dest="status", default=[])
        parser.add_argument("--device", nargs="*", dest="device", default=[])

        bots = parser.add_mutually_exclusive_group()
        bots.add_argument("--only-bots", dest="bots", action="store_true")
        bots.add_argument("--no-bots", dest="nbots", action="store_true")

        parser.add_argument("--activity-type", nargs="*", dest="at", default=[])
        parser.add_argument("--activity", nargs="*", dest="a", default=[])

        at = parser.add_mutually_exclusive_group()
        at.add_argument("--no-activity", dest="na", action="store_true")
        at.add_argument("--an-activity", dest="aa", action="store_true")

        # Permissions
        parser.add_argument("--perms", nargs="*", dest="perms", default=[])
        parser.add_argument("--any-perm", nargs="*", dest="any-perm", default=[])

        parser.add_argument("--not-perms", nargs="*", dest="not-perms", default=[])
        parser.add_argument("--not-any-perm", nargs="*", dest="not-any-perm", default=[])

        # Extra
        parser.add_argument("--format", nargs="*", dest="format", default=["page"])

        try:
            vals = vars(parser.parse_args(argument.split(" ")))
        except Exception as exc:
            raise BadArgument() from exc

        try:
            for key, value in vals.items():
                if type(value) == list:
                    split_words = value
                    word_list = []
                    tmp = ""
                    for word in split_words:
                        if not word.startswith('"') and not word.endswith('"') and not tmp:
                            if word.startswith(r"\""):
                                word = word[1:]
                            word_list.append(word)
                        else:
                            echanged = False
                            if word.endswith(r"\""):
                                word = word[:-2] + '"'
                                echanged = True

                            schanged = False
                            if word.startswith(r"\""):
                                word = word[1:]
                                schanged = True
                            if word.startswith('"') and not schanged:
                                if word.startswith('"') and word.endswith('"') and len(word) > 1:
                                    word_list.append(word)
                                else:
                                    if tmp.endswith(" "):
                                        word_list.append(tmp)
                                        tmp = ""
                                        continue
                                    tmp += word[1:] + " "
                            elif word.endswith('"') and not echanged:
                                tmp += word[:-1]
                                word_list.append(tmp)
                                tmp = ""
                            else:
                                if schanged or echanged:
                                    word_list.append(word)
                                    continue
                                tmp += word + " "
                    if tmp:
                        raise BadArgument("A quote was started but never finished.")
                    vals[key] = word_list
        except Exception as e:
            raise BadArgument(str(e))

        if any(s for s in vals["status"] if not s.lower() in ["online", "dnd", "idle", "offline"]):
            raise BadArgument(
                "Invalid status.  Must be either `online`, `dnd`, `idle` or `offline`."
            )

        # Useeeeeeeeeeeeeeeeeeeernames (and Stuff)
        if vals["disc"]:
            new = []
            for disc in vals["disc"]:
                if len(disc) != 4:
                    raise BadArgument("Discriminators must have the length of 4")
                try:
                    new.append(int(disc))
                except ValueError:
                    raise BadArgument("Discriminators must be valid integers")
            vals["disc"] = new

        if vals["ndisc"]:
            new = []
            for disc in vals["ndisc"]:
                if len(disc) != 4:
                    raise BadArgument("Discriminators must have the length of 4")
                try:
                    new.append(int(disc))
                except ValueError:
                    raise BadArgument("Discriminators must be valid integers")
            vals["ndisc"] = new

        # Rooooooooooooooooles

        rc = RoleConverter()
        new = []
        for role in vals["roles"]:
            r = await rc.convert(ctx, role)
            if not r:
                raise BadArgument(f"Couldn't find a role matching: {role}")
            new.append(r)
        vals["roles"] = new

        new = []
        for role in vals["any-role"]:
            r = await rc.convert(ctx, role)
            if not r:
                raise BadArgument(f"Couldn't find a role matching: {role}")
            new.append(r)
        vals["any-role"] = new

        new = []
        for role in vals["not-roles"]:
            r = await rc.convert(ctx, role)
            if not r:
                raise BadArgument(f"Couldn't find a role matching: {role}")
            new.append(r)
        vals["not-roles"] = new

        new = []
        for role in vals["not-any-role"]:
            r = await rc.convert(ctx, role)
            if not r:
                raise BadArgument(f"Couldn't find a role matching: {role}")
            new.append(r)
        vals["not-any-role"] = new

        # Daaaaaaaaaaaaaaaaaates

        if vals["joined-on"]:
            if len(vals["joined-on"]) != 3:
                raise BadArgument(
                    "Invalid amount of digits for the `joined-on` date.  Must be `YYYY MM DD`"
                )
            try:
                vals["joined-on"] = list(map(int, vals["joined-on"]))
            except ValueError:
                raise BadArgument("Dates must be integers.")
            if not vals["joined-on"][1] in range(1, 13):
                raise BadArgument("Month must be between 1 and 12")
            if not vals["joined-on"][2] in range(1, 32):
                raise BadArgument("Day must be between 1 and 31")

        if vals["joined-be"]:
            if len(vals["joined-be"]) != 3:
                raise BadArgument(
                    "Invalid amount of digits for the `joined-before` date.  Must be `YYYY MM DD`"
                )
            try:
                vals["joined-be"] = list(map(int, vals["joined-be"]))
            except ValueError:
                raise BadArgument("Dates must be integers.")
            if not vals["joined-be"][1] in range(1, 13):
                raise BadArgument("Month must be between 1 and 12")
            if not vals["joined-be"][2] in range(1, 32):
                raise BadArgument("Day must be between 1 and 31")

        if vals["joined-af"]:
            if len(vals["joined-af"]) != 3:
                raise BadArgument(
                    "Invalid amount of digits for the `joined-after` date.  Must be `YYYY MM DD`"
                )
            try:
                vals["joined-af"] = list(map(int, vals["joined-af"]))
            except ValueError:
                raise BadArgument("Dates must be integers.")
            if not vals["joined-af"][1] in range(1, 13):
                raise BadArgument("Month must be between 1 and 12")
            if not vals["joined-af"][2] in range(1, 32):
                raise BadArgument("Day must be between 1 and 31")

        if vals["created-on"]:
            if len(vals["created-on"]) != 3:
                raise BadArgument(
                    "Invalid amount of digits for the `created-on` date.  Must be `YYYY MM DD`"
                )
            try:
                vals["created-on"] = list(map(int, vals["created-on"]))
            except ValueError:
                raise BadArgument("Dates must be integers.")
            if not vals["created-on"][1] in range(1, 13):
                raise BadArgument("Month must be between 1 and 12")
            if not vals["created-on"][2] in range(1, 32):
                raise BadArgument("Day must be between 1 and 31")

        if vals["created-be"]:
            if len(vals["created-be"]) != 3:
                raise BadArgument(
                    "Invalid amount of digits for the `created-before` date.  Must be `YYYY MM DD`"
                )
            try:
                vals["created-be"] = list(map(int, vals["created-be"]))
            except ValueError:
                raise BadArgument("Dates must be integers.")
            if not vals["created-be"][1] in range(1, 13):
                raise BadArgument("Month must be between 1 and 12")
            if not vals["created-be"][2] in range(1, 32):
                raise BadArgument("Day must be between 1 and 31")

        if vals["created-af"]:
            if len(vals["created-af"]) != 3:
                raise BadArgument(
                    "Invalid amount of digits for the `created-after` date.  Must be `YYYY MM DD`"
                )
            try:
                vals["created-af"] = list(map(int, vals["created-af"]))
            except ValueError:
                raise BadArgument("Dates must be integers.")
            if not vals["created-af"][1] in range(1, 13):
                raise BadArgument("Month must be between 1 and 12")
            if not vals["created-af"][2] in range(1, 32):
                raise BadArgument("Day must be between 1 and 31")

        # Actiiiiiiiiiiiiiiiiivities
        if vals["device"]:
            if not all(d in ["desktop", "mobile", "web"] for d in vals["device"]):
                raise BadArgument("Bad device.  Must be `desktop`, `mobile` or `web`.")

        if vals["at"]:
            at = discord.ActivityType
            switcher = {
                "unknown": at.unknown,
                "playing": at.playing,
                "streaming": at.streaming,
                "listening": at.listening,
                "watching": at.watching,
            }
            if not all([a.lower() in switcher for a in vals["at"]]):
                raise BadArgument(
                    "Invalid Activity Type.  Must be either `unknown`, `playing`, `streaming`, `listening` or `watching`."
                )
            new = [switcher[name.lower()] for name in vals["at"]]
            vals["at"] = new

        new = []
        for perm in vals["perms"]:
            perm = perm.replace(" ", "_")
            if not perm.lower() in PERMS:
                raise BadArgument(
                    f"Invalid permission.  Run `{ctx.prefix}target permissions` to see a list of valid permissions."
                )
            new.append(perm)
        vals["perms"] = new

        new = []
        for perm in vals["any-perm"]:
            perm = perm.replace(" ", "_")
            if not perm.lower() in PERMS:
                raise BadArgument(
                    f"Invalid permission.  Run `{ctx.prefix}target permissions` to see a list of valid permissions."
                )
            new.append(perm)
        vals["any-perm"] = new

        new = []
        for perm in vals["not-perms"]:
            perm = perm.replace(" ", "_")
            if not perm.lower() in PERMS:
                raise BadArgument(
                    f"Invalid permission.  Run `{ctx.prefix}target permissions` to see a list of valid permissions."
                )
            new.append(perm)
        vals["not-perms"] = new

        new = []
        for perm in vals["not-any-perm"]:
            perm = perm.replace(" ", "_")
            if not perm.lower() in PERMS:
                raise BadArgument(
                    f"Invalid permission.  Run `{ctx.prefix}target permissions` to see a list of valid permissions."
                )
            new.append(perm)
        vals["not-any-perm"] = new

        if vals["format"]:
            if not vals["format"][0].lower() in ["page", "menu"]:
                raise BadArgument(
                    "Invalid format.  Must be `page` for in a bin or `menu` for in an embed."
                )
            vals["format"] = vals["format"][0].lower()

        return vals


class Targeter(commands.Cog):
    """Target members and get a list of them based on the passed arguments"""

    def __init__(self, bot):
        self.bot = bot
        self.conv = Args()  # For evals
        self.s = aiohttp.ClientSession()

    async def post(self, string):
        async with self.s.put("http://bin.doyle.la", data=string.encode("utf-8")) as post:
            text = await post.text()
        return text

    def lookup(self, ctx, args):
        matched = ctx.guild.members
        passed = []
        # --- Go through each possible argument ---

        # -- Nicknames/Usernames --

        if args["nick"]:
            matched_here = []
            for user in matched:
                if any(
                    [user.nick and piece.lower() in user.nick.lower() for piece in args["nick"]]
                ):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["user"]:
            matched_here = []
            for user in matched:
                if any([piece.lower() in user.name.lower() for piece in args["user"]]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["name"]:
            matched_here = []
            for user in matched:
                if any([piece.lower() in user.display_name.lower() for piece in args["name"]]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["not-nick"]:
            matched_here = []
            for user in matched:
                if not any(
                    [
                        user.nick and piece.lower() in user.nick.lower()
                        for piece in args["not-nick"]
                    ]
                ):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["not-user"]:
            matched_here = []
            for user in matched:
                if not any([piece.lower() in user.name.lower() for piece in args["not-user"]]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["not-name"]:
            matched_here = []
            for user in matched:
                if not any(
                    [piece.lower() in user.display_name.lower() for piece in args["not-name"]]
                ):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["a-nick"]:
            matched_here = []
            for user in matched:
                if user.nick:
                    matched_here.append(user)
            passed.append(matched_here)

        if args["no-nick"]:
            matched_here = []
            for user in matched:
                if not user.nick:
                    matched_here.append(user)
            passed.append(matched_here)

        if args["disc"]:
            matched_here = []
            for user in matched:
                if any([disc == int(user.discriminator) for disc in args["disc"]]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["ndisc"]:
            matched_here = []
            for user in matched:
                if not any([disc == int(user.discriminator) for disc in args["ndisc"]]):
                    matched_here.append(user)
            passed.append(matched_here)

        # -- End Nicknames/Usernames --

        # -- Roles --

        if args["roles"]:
            matched_here = []
            for user in matched:
                ur = [role.id for role in user.roles]
                if all(role.id in ur for role in args["roles"]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["any-role"]:
            matched_here = []
            for user in matched:
                ur = [role.id for role in user.roles]
                if any(role.id in ur for role in args["any-role"]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["not-roles"]:
            matched_here = []
            for user in matched:
                ur = [role.id for role in user.roles]
                if not all(role.id in ur for role in args["not-roles"]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["not-any-role"]:
            matched_here = []
            for user in matched:
                ur = [role.id for role in user.roles]
                if not any(role.id in ur for role in args["not-any-role"]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["a-role"]:
            matched_here = []
            for user in matched:
                if len(user.roles) > 1:  # Since all members have the @everyone role
                    matched_here.append(user)
            passed.append(matched_here)

        if args["no-role"]:
            matched_here = []
            for user in matched:
                if len(user.roles) == 1:  # Since all members have the @everyone role
                    matched_here.append(user)
            passed.append(matched_here)

        # -- End Roles --

        # -- Dates --

        if args["joined-on"]:
            a = args["joined-on"]
            matched_here = []
            for user in matched:
                j = user.joined_at
                if j.year == a[0] and j.month == a[1] and j.day == a[2]:
                    matched_here.append(user)
            passed.append(matched_here)

        if args["joined-be"]:
            a = args["joined-be"]
            matched_here = []
            for user in matched:
                j = user.joined_at
                if j.year < a[0]:
                    matched_here.append(user)
                elif j.month < a[1] and j.year == a[0]:
                    matched_here.append(user)
                elif j.day < a[2] and j.year == a[0] and j.month == a[1]:
                    matched_here.append(user)
                else:
                    pass
            passed.append(matched_here)

        if args["joined-af"]:
            a = args["joined-af"]
            matched_here = []
            for user in matched:
                j = user.joined_at
                if j.year > a[0]:
                    matched_here.append(user)
                elif j.month > a[1] and j.year == a[0]:
                    matched_here.append(user)
                elif j.day > a[2] and j.year == a[0] and j.month == a[1]:
                    matched_here.append(user)
                else:
                    pass
            passed.append(matched_here)

        if args["created-on"]:
            a = args["created-on"]
            matched_here = []
            for user in matched:
                j = user.created_at
                if j.year == a[0] and j.month == a[1] and j.day == a[2]:
                    matched_here.append(user)
            passed.append(matched_here)

        if args["created-be"]:
            a = args["created-be"]
            matched_here = []
            for user in matched:
                j = user.created_at
                if j.year < a[0]:
                    matched_here.append(user)
                elif j.month < a[1] and j.year == a[0]:
                    matched_here.append(user)
                elif j.day < a[2] and j.year == a[0] and j.month == a[1]:
                    matched_here.append(user)
                else:
                    pass
            passed.append(matched_here)

        if args["created-af"]:
            a = args["created-af"]
            matched_here = []
            for user in matched:
                j = user.created_at
                if j.year > a[0]:
                    matched_here.append(user)
                elif j.month > a[1] and j.year == a[0]:
                    matched_here.append(user)
                elif j.day > a[2] and j.year == a[0] and j.month == a[1]:
                    matched_here.append(user)
                else:
                    pass
            passed.append(matched_here)

        # -- End Dates --

        # -- Statuses / Activities --

        if args["status"]:
            matched_here = []
            statuses = [s for s in discord.Status if s.name.lower() in args["status"]]
            for user in matched:
                if user.status in statuses:
                    matched_here.append(user)
            passed.append(matched_here)

        if args["device"]:
            matched_here = []
            for user in matched:
                for d in args["device"]:
                    s = getattr(user, f"{d}_status")
                    if str(s) != "offline":
                        matched_here.append(user)
            passed.append(matched_here)

        if args["bots"]:
            matched_here = []
            for user in matched:
                if user.bot:
                    matched_here.append(user)
            passed.append(matched_here)

        if args["nbots"]:
            matched_here = []
            for user in matched:
                if not user.bot:
                    matched_here.append(user)
            passed.append(matched_here)

        if args["at"]:
            matched_here = []
            for user in matched:
                if (user.activity) and (user.activity.type in args["at"]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["a"]:
            matched_here = []
            for user in matched:
                if (user.activity) and (
                    user.activity.name.lower() in [a.lower() for a in args["a"]]
                ):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["na"]:
            matched_here = []
            for user in matched:
                if not user.activity:
                    matched_here.append(user)
            passed.append(matched_here)

        if args["aa"]:
            matched_here = []
            for user in matched:
                if user.activity:
                    matched_here.append(user)
            passed.append(matched_here)

        # -- End Statuses / Activities --

        # -- Permissions --
        if args["perms"]:
            matched_here = []
            for user in matched:
                up = user.guild_permissions
                if all(getattr(up, perm) for perm in args["perms"]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["any-perm"]:
            matched_here = []
            for user in matched:
                up = user.guild_permissions
                if any(getattr(up, perm) for perm in args["any-perm"]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["not-perms"]:
            matched_here = []
            for user in matched:
                up = user.guild_permissions
                if not all(getattr(up, perm) for perm in args["not-perms"]):
                    matched_here.append(user)
            passed.append(matched_here)

        if args["not-any-perm"]:
            matched_here = []
            for user in matched:
                up = user.guild_permissions
                if not any(getattr(up, perm) for perm in args["not-any-perm"]):
                    matched_here.append(user)
            passed.append(matched_here)

        # --- End going through possible arguments ---
        try:
            all_passed = set(passed.pop())
        except IndexError:
            return []
        return all_passed.intersection(*passed)

    @checks.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def target(self, ctx, *, args: Args):
        """Targets users based on the passed arguments.
        
        Run `[p]target help` to see a list of valid arguments."""
        # await ctx.send(args)
        async with ctx.typing():
            compact = functools.partial(self.lookup, ctx, args)
            matched = await self.bot.loop.run_in_executor(None, compact)

            if len(matched) != 0:
                color = await ctx.embed_color()
                if args["format"] == "page":
                    string = "The following users have matched your arguments:\n"
                    for number, member in enumerate(matched, 1):
                        adding = f"Entry #{number}\n    • Username: {member.name}\n    • Guild Name: {member.display_name}\n    • ID: {member.id}\n"
                        string += adding
                    url = await self.post(string)
                    embed = discord.Embed(
                        title="Targeting complete",
                        description=f"Found {len(matched)} matches.  Click [here]({url}) to see the full results.",
                        color=color,
                    )
                    m = False
                else:
                    string = " ".join([m.mention for m in matched])
                    embed_list = []
                    for page in pagify(string, delims=[" "], page_length=750):
                        embed = discord.Embed(
                            title=f"Targeting complete.  Found {len(matched)} matches.",
                            color=color,
                        )
                        embed.description = page
                        embed_list.append(embed)
                    m = True
            else:
                embed = discord.Embed(
                    title="Targeting complete", description=f"Found no matches.", color=0xFF0000
                )
                m = False
        if not m:
            await ctx.send(embed=embed)
        else:
            await menu(ctx, embed_list, DEFAULT_CONTROLS)

    @target.command(name="help")
    async def _help(self, ctx):
        """Returns a menu that has a list of arguments you can pass to `[p]target`"""
        embed_list = []

        names = discord.Embed(title="Target Arguments - Names")
        desc = (
            "`--nick <nickone> <nicktwo>` - Users must have one of the passed nicks in their nickname.  If they don't have a nickname, they will instantly be excluded.\n"
            "`--user <userone> <usertwo>` - Users must have one of the passed usernames in their real username.  This will not look at nicknames.\n"
            "`--name <nameone> <nametwo>` - Users must have one of the passed names in their username, and if they don't have one, their username.\n"
            "\n"
            "`--not-nick <nickone> <nicktwo>` - Users must not have one of the passed nicks in their nickname.  If they don't have a nickname, they will instantly be excluded.\n"
            "`--not-user <userone> <usertwo>` - Users must not have one of the passed usernames in their real username.  This will not look at nicknames.\n"
            "`--not-name <nameone> <nametwo>` - Users must not have one of the passed names in their username, and if they don't have one, their username.\n"
            "\n"
            "`--a-nick` - Users must have a nickname in the server.\n"
            "`--no-nick` - Users cannot have a nickname in the server."
        )
        names.description = desc
        names.set_footer(text="Target Arguments - Names; Page 1/6")
        embed_list.append(names)

        roles = discord.Embed(title="Target Arguments - Roles")
        desc = (
            "`--roles <roleone> <roletwo>` - Users must have all of the roles provided.\n"
            "`--any-role <roleone> <roletwo>` - Users must have at least one of the roles provided.\n"
            "`--a-role` - Users must have at least one role\n"
            "\n"
            "`--not-roles <roleone> <roletwo>` - Users cannot have all of the roles provided.\n"
            "`--not-any-role <roleone> <roletwo>` - Users cannot have any of the roles provided.\n"
            "`--no-role` - Users cannot have any roles."
        )
        roles.description = desc
        roles.set_footer(text="Target Arguments - Roles; Page 2/6")
        embed_list.append(roles)

        status = discord.Embed(title="Target Arguments - Profile")
        desc = (
            "`--status <offline> <online> <dnd> <idle>` - Users' status must have at least one of the statuses passed.\n"
            "`--device <mobile> <web> <desktop>` - Filters by their device statuses.  If they are not offline on any of the ones specified, they are included.\n"
            "`--only-bots` - Users must be a bot.\n"
            "`--no-bots` - Users cannot be a bot.\n"
            "\n"
            '`--activity "name of activity" "another one"` - Users\' activity must contain one of the activities passed.\n'
            "`--activity-type <playing> <streaming> <watching> <listening>` - Users' activity types must be one of the ones passed.\n"
            "`--an-activity` - Users must be in an activity.\n"
            "`--no-activity` - Users cannot be in an activity.\n"
        )
        status.description = desc
        status.set_footer(text="Target Arguments - Profile; Page 3/6")
        embed_list.append(status)

        dates = discord.Embed(title="Target Arguments - Dates")
        desc = (
            "`--joined-on YYYY MM DD` - Users must have joined on the day specified.\n"
            "`--joined-before YYYY MM DD` - Users must have joined before the day specified.  The day specified is not counted.\n"
            "`--joined-after YYYY MM DD` - Users must have joined after the day specified.  The day specified is not counted.\n"
            "\n"
            "`--created-on YYYY MM DD` - Users must have created their account on the day specified.\n"
            "`--created-before YYYY MM DD` - Users must have created their account before the day specified.  The day specified is not counted.\n"
            "`--created-after YYYY MM DD` - Users must have created their account after the day specified.  The day specified is not counted."
        )
        dates.description = desc
        dates.set_footer(text="Target Arguments - Dates; Page 4/6")
        embed_list.append(dates)

        perms = discord.Embed(title="Target Arguments - Permissions")
        desc = (
            "`--perms` - Users must have all of the permissions passed.\n"
            "`--any-perm` - Users must have at least one of the permissions passed.\n"
            "\n"
            "`--not-perms` - Users cannot have all of the permissions passed.\n"
            "`--not-any-perm` - Users cannot have any of the permissions passed.\n"
            "\n"
            f"Run `{ctx.prefix}target permissions` to see a list of permissions that can be passed."
        )
        perms.description = desc
        perms.set_footer(text="Target Arguments - Permissions; Page 5/6")
        embed_list.append(perms)

        special = discord.Embed(title="Target Arguments - Special Notes")
        desc = (
            "`--format` - How to display results.  At the moment, must be `page` for posting on a website, or `menu` for showing the results in Discord.\n"
            "\n"
            "If at any time you need to include quotes at the beginning or ending of something (such as a nickname or a role), include a slash (\) right before it."
        )
        special.description = desc
        special.set_footer(text="Target Arguments - Special Notes; Page 6/6")
        embed_list.append(special)

        await menu(ctx, embed_list, DEFAULT_CONTROLS)

    @target.command()
    async def permissions(self, ctx):
        """Returns a list of permissions that can be passed to `[p]target`"""
        perms = [p.replace("_", " ") for p in PERMS]
        embed = discord.Embed(title="Permissions that can be passed to Targeter")
        embed.description = humanize_list(perms)
        await ctx.send(embed=embed)
