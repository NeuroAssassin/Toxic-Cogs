from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.commands import BadArgument, Converter, RoleConverter
from redbot.core import commands
from datetime import datetime
import functools
import aiohttp
import argparse
import discord
import re


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

        # Status / Activity / Device
        parser.add_argument("--status", nargs="*", dest="status", default=[])
        parser.add_argument("--device", nargs="*", dest="device", default=[])

        parser.add_argument("--activity-type", nargs="*", dest="at", default=[])
        parser.add_argument("--activity", nargs="*", dest="a", default=[])

        at = parser.add_mutually_exclusive_group()
        at.add_argument("--no-activity", dest="na", action="store_true")
        at.add_argument("--an-activity", dest="aa", action="store_true")

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
                            word_list.append(word)
                        else:
                            if word.startswith('"'):
                                tmp += word[1:] + " "
                            elif word.endswith('"'):
                                tmp += word[:-1]
                                word_list.append(tmp)
                                tmp = ""
                            else:
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

        if vals["joined-be"]:
            if len(vals["joined-be"]) != 3:
                raise BadArgument(
                    "Invalid amount of digits for the `joined-before` date.  Must be `YYYY MM DD`"
                )
            try:
                vals["joined-be"] = list(map(int, vals["joined-be"]))
            except ValueError:
                raise BadArgument("Dates must be integers.")

        if vals["joined-af"]:
            if len(vals["joined-af"]) != 3:
                raise BadArgument(
                    "Invalid amount of digits for the `joined-after` date.  Must be `YYYY MM DD`"
                )
            try:
                vals["joined-af"] = list(map(int, vals["joined-af"]))
            except ValueError:
                raise BadArgument("Dates must be integers.")

        if vals["created-on"]:
            if len(vals["created-on"]) != 3:
                raise BadArgument(
                    "Invalid amount of digits for the `created-on` date.  Must be `YYYY MM DD`"
                )
            try:
                vals["created-on"] = list(map(int, vals["created-on"]))
            except ValueError:
                raise BadArgument("Dates must be integers.")

        if vals["created-be"]:
            if len(vals["created-be"]) != 3:
                raise BadArgument(
                    "Invalid amount of digits for the `created-before` date.  Must be `YYYY MM DD`"
                )
            try:
                vals["created-be"] = list(map(int, vals["created-be"]))
            except ValueError:
                raise BadArgument("Dates must be integers.")

        if vals["created-af"]:
            if len(vals["created-af"]) != 3:
                raise BadArgument(
                    "Invalid amount of digits for the `created-after` date.  Must be `YYYY MM DD`"
                )
            try:
                vals["created-af"] = list(map(int, vals["created-af"]))
            except ValueError:
                raise BadArgument("Dates must be integers.")

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

        return vals


class Targeter(commands.Cog):
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

        # --- End going through possible arguments ---
        try:
            all_passed = set(passed.pop())
        except IndexError:
            return []
        return all_passed.intersection(*passed)

    @commands.group(invoke_without_command=True)
    async def target(self, ctx, *, args: Args):
        """Targets users based on the passed arguments.
        
        Run `[p]target help` to see a list of valid arguments."""
        # await ctx.send(args)
        async with ctx.typing():
            compact = functools.partial(self.lookup, ctx, args)
            matched = await self.bot.loop.run_in_executor(None, compact)

            if len(matched) != 0:
                string = "The following users have matched your arguments:\n"
                for number, member in enumerate(matched, 1):
                    adding = f"Entry #{number}\n    • Username: {member.name}\n    • Guild Name: {member.display_name}\n    • ID: {member.id}\n"
                    string += adding
                url = await self.post(string)
                if len(matched) < 500:
                    color = 0x00FF00
                elif len(matched) < 1000:
                    color = 0xFFA500
                else:
                    color = 0xFF0000
                embed = discord.Embed(
                    title="Targeting complete",
                    description=f"Found {len(matched)} matches.  Click [here]({url}) to see the full results.",
                    color=color,
                )
            else:
                embed = discord.Embed(
                    title="Targeting complete", description=f"Found no matches.", color=0xFF0000
                )
        await ctx.send(embed=embed)

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
            "`--not-name <nameone> <nametwo>` - Users must not have one of the passed names in their username, and if they don't have one, their username."
        )
        names.description = desc
        names.set_footer(text="Target Arguments - Names; Page 1/4")
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
        roles.set_footer(text="Target Arguments - Roles; Page 2/4")
        embed_list.append(roles)

        status = discord.Embed(title="Target Arguments - Status")
        desc = (
            "`--status <offline> <online> <dnd> <idle>` - Users' status must have at least one of the statuses passed.\n"
            "`--device <mobile> <web> <desktop>` - Filters by their device statuses.  If they are not offline on any of the ones specified, they are included.\n"
            "\n"
            '`--activity "name of activity" "another one"` - Users\' activity must contain one of the activities passed.\n'
            "`--activity-type <playing> <streaming> <watching> <listening>` - Users' activity types must be one of the ones passed.\n"
            "`--an-activity` - Users must be in an activity.\n"
            "`--no-activity` - Users cannot be in an activity.\n"
        )
        status.description = desc
        status.set_footer(text="Target Arguments - Status; Page 3/4")
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
        dates.set_footer(text="Target Arguments - Dates; Page 4/4")
        embed_list.append(dates)

        await menu(ctx, embed_list, DEFAULT_CONTROLS)
