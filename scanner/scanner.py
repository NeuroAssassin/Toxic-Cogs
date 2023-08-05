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

import contextlib
import copy
import io
import re
import traceback

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_list, inline

URL = "https://api.sightengine.com/1.0/check.json"
TEXT_URL = "https://api.sightengine.com/1.0/text/check.json"

TEXT_MODERATION_CHECKS = [
    "sexual",
    "insult",
    "discriminatory",
    "innapropriate",
    "other_profanity",
    "email",
    "ipv4",
    "ipv6",
    "phone_number_us",
    "phone_number_uk",
    "phone_number_fr",
    "ssn",
]


class Scanner(commands.Cog):
    """Scan images as they are sent through according to the set models."""

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=473541068378341376)

        default_global = {"userkey": "", "secret": ""}
        self.conf.register_global(**default_global)

        default_guild = {
            "nude": False,
            "partial": True,
            "wad": False,
            "offensive": False,
            "scammer": False,
            "textmoderation": {"checks": [], "enabled": False},
            "rawtextmoderation": {"checks": [], "lang": "en", "enabled": False},
            "channel": 0,
            "percent": 70,
            "autodelete": True,
            "showpic": False,
            "roles": [],
            "whitelist": [],
            "blacklist": [],
        }
        self.conf.register_guild(**default_guild)

        self.regex = re.compile(r"^.*\.(.*)")

    async def red_delete_data_for_user(self, **kwargs):
        """This cog does not store user data"""
        return

    # Text listener
    @commands.Cog.listener("on_message")
    async def text_on_message(self, message):
        if message.author.id == self.bot.user.id:
            return

        try:
            if not message.guild:
                return

            if not message.content:
                return

            settings = await self.conf.guild(message.guild).all()
            if not (
                settings["rawtextmoderation"]["enabled"]
                and settings["rawtextmoderation"]["enabled"]
            ):
                return
            if settings["whitelist"] and message.channel.id not in settings["whitelist"]:
                return
            if message.channel.id in settings["blacklist"]:
                return

            data = await self.conf.all()
            user = data["userkey"]
            secret = data["secret"]
            if not (user and secret):
                return

            params = {
                "text": message.content,
                "lang": settings["rawtextmoderation"]["lang"],
                "mode": "standard",
                "api_user": user,
                "api_secret": secret,
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(TEXT_URL, params=params) as request:
                    returned = request
                    json = await returned.json()
            if returned.status != 200 or json["status"] != "success":
                await message.channel.send(f"Error, code {returned.status} on message processing.")

            tm_violations = []
            tm_builder = ""

            for profanity in json["profanity"]["matches"]:
                if profanity["type"] in settings["rawtextmoderation"]["checks"]:
                    tm_violations.append((profanity["type"], profanity["match"]))

            for personal in json["personal"]["matches"]:
                if personal["type"] in settings["rawtextmoderation"]["checks"]:
                    textmoderation = True
                    tm_violations.append((personal["type"], personal["match"]))

            if tm_violations:
                tm_builder = ""
                for violation in tm_violations:
                    tm_builder += f"Message Moderation ({violation[0]}): {violation[1]}\n"

                deleted = False
                if settings["autodelete"]:
                    with contextlib.suppress(discord.HTTPException):
                        await message.delete()
                        deleted = True
                channel = self.bot.get_channel(settings["channel"])
                if channel:
                    embed = discord.Embed(
                        title="Scanner detected a violating message.",
                        description=f"Author: {message.author.mention}\nChannel: {message.channel.mention}",
                    )
                    embed.add_field(name="Content", value=message.content)
                    embed.add_field(name="Violating:", value=tm_builder)
                    if not deleted:
                        embed.add_field(
                            name="Message was not deleted",
                            value=f"Here's a jump url: [Click Here]({message.jump_url})",
                        )
                    content = None
                    if settings["roles"]:
                        content = ", ".join(
                            [
                                message.guild.get_role(r).mention
                                for r in settings["roles"]
                                if message.guild.get_role(r)
                            ]
                        )
                    await channel.send(
                        content=content,
                        embed=embed,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=False, users=False, roles=True
                        ),
                    )
        except Exception as error:
            await message.channel.send("Error")
            await message.channel.send(
                "".join(traceback.format_exception(type(error), error, error.__traceback__))
            )

    # Image listener
    @commands.Cog.listener("on_message")
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return

        try:
            if not message.guild:
                return
            if not message.attachments:
                return

            settings = await self.conf.guild(message.guild).all()
            if settings["whitelist"] and message.channel.id not in settings["whitelist"]:
                return
            if message.channel.id in settings["blacklist"]:
                return

            data = await self.conf.all()
            user = data["userkey"]
            secret = data["secret"]
            if not (user and secret):
                return

            s = ""
            if settings["channel"] == 0:
                return
            if settings["nude"]:
                s += "nudity,"
            if settings["wad"]:
                s += "wad,"
            if settings["offensive"]:
                s += "offensive,"
            if settings["scammer"]:
                s += "scam,"
            if settings["textmoderation"]["enabled"] and settings["textmoderation"]["checks"]:
                s += "text-content,"
            if s == "":
                return
            s = s[:-1]  # Remove the extra ,

            for attach in message.attachments:
                match = self.regex.match(attach.filename)
                if not match:
                    continue
                ext = match.group(1)
                if not ext.lower() in ["jpg", "png", "webp", "jpeg"]:
                    continue

                nudity = False
                partial = False
                wad = False
                offensive = False
                scammer = False
                tm_violations = []
                params = {
                    "models": s,
                    "url": attach.url,
                    "api_user": user,
                    "api_secret": secret,
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(URL, params=params) as request:
                        returned = request
                        json = await returned.json()
                if json.get("nudity"):
                    nudity = json["nudity"]
                    if nudity["raw"] >= max(nudity["partial"], nudity["safe"]):
                        nudity = True
                    elif nudity["partial"] >= max(nudity["raw"], nudity["safe"]):
                        if settings["partial"]:
                            partial = True
                    else:
                        nudity = False
                if json.get("weapon"):
                    if json["weapon"] * 100 >= settings["percent"]:
                        wad = True
                if json.get("alcohol"):
                    if json["alcohol"] * 100 >= settings["percent"]:
                        wad = True
                if json.get("drugs"):
                    if json["drugs"] * 100 >= settings["percent"]:
                        wad = True
                if json.get("offensive"):
                    if json["offensive"]["prob"] * 100 >= settings["percent"]:
                        offensive = True
                if json.get("scam"):
                    if json["scam"]["prob"] * 100 >= settings["percent"]:
                        scammer = True
                if json.get("text"):
                    tm_builder = ""

                    for profanity in json["text"]["profanity"]:
                        if profanity["type"] in settings["textmoderation"]["checks"]:
                            tm_violations.append((profanity["type"], profanity["match"]))

                    for personal in json["text"]["personal"]:
                        if personal["type"] in settings["textmoderation"]["checks"]:
                            tm_violations.append((personal["type"], personal["match"]))

                    if tm_violations:
                        tm_builder = ""
                        for violation in tm_violations:
                            tm_builder += f"Text Moderation ({violation[0]}): {violation[1]}\n"

                if nudity or partial or wad or offensive or scammer or tm_violations:
                    if settings["showpic"]:
                        b = io.BytesIO(await attach.read())
                        f = discord.File(filename=attach.filename, fp=b)
                    deleted = False
                    if settings["autodelete"]:
                        with contextlib.suppress(discord.HTTPException):
                            await message.delete()
                            deleted = True
                    channel = self.bot.get_channel(settings["channel"])
                    if channel:
                        embed = discord.Embed(
                            title="Scanner detected a violating image.",
                            description=f"Author: {message.author.mention}\nChannel: {message.channel.mention}",
                        )
                        if settings["showpic"]:
                            embed.set_image(url=f"attachment://{attach.filename}")
                        violating = (
                            "Nudity\n"
                            if nudity
                            else "" "Partial Nudity\n"
                            if partial
                            else "" "WAD\n"
                            if wad
                            else "" "Offensive\n"
                            if offensive
                            else "" "Scammer\n"
                            if scammer
                            else "" f"{tm_builder}"
                            if tm_violations
                            else ""
                        )
                        embed.add_field(name="Violating:", value=violating)
                        if not deleted:
                            embed.add_field(
                                name="Message was not deleted",
                                value=f"Here's a jump url: [Click Here]({message.jump_url})",
                            )
                        content = None
                        if settings["roles"]:
                            content = ", ".join(
                                [
                                    message.guild.get_role(r).mention
                                    for r in settings["roles"]
                                    if message.guild.get_role(r)
                                ]
                            )
                        if settings["showpic"]:
                            await channel.send(content=content, embed=embed, file=f)
                        else:
                            await channel.send(content=content, embed=embed)
        except Exception as error:
            await message.channel.send("Error")
            await message.channel.send(
                "".join(traceback.format_exception(type(error), error, error.__traceback__))
            )

    @commands.admin_or_permissions(manage_messages=True)
    @commands.group()
    async def scanner(self, ctx):
        """Group command for changing scanner's settings."""
        pass

    @scanner.group()
    async def report(self, ctx):
        """Manage how reports are handled, and base reasons for deletion for messages being deleted."""
        pass

    @report.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set the channel for reports to go to."""
        await self.conf.guild(ctx.guild).channel.set(channel.id)
        await ctx.tick()

    @report.command()
    async def autodelete(self, ctx, yes_or_no: bool):
        """Set whether the messages should be auto deleted and reported or just reported."""
        await self.conf.guild(ctx.guild).autodelete.set(yes_or_no)
        if yes_or_no:
            await ctx.send(
                "Messages will now be auto-deleted if they are marked as a violation of the set rules."
            )
        else:
            await ctx.send(
                "Messages will now not be auto-deleted even if they are marked as a violation of the set rules."
            )

    @report.command()
    async def percent(self, ctx, percent: int):
        """Set the percent a picture must have in order to be violating.  100 means full violation, 0 is no violation"""
        if percent < 1 or percent > 100:
            return await ctx.send("Must be between 1 and 100")
        await self.conf.guild(ctx.guild).percent.set(percent)

    @report.command()
    async def showpic(self, ctx, yes_or_no: bool):
        """Set whether or not to show the violating picture in the report."""
        await self.conf.guild(ctx.guild).showpic.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Pictures will now be shown in the report.")
        else:
            await ctx.send("Messages will now not be shown in the report.")

    @report.command()
    async def pingrole(self, ctx, *, role: discord.Role = None):
        """Add or remove roles from being pinged when a report is sent."""
        if role:
            async with self.conf.guild(ctx.guild).roles() as roles:
                if role.id in roles:
                    roles.remove(role.id)
                    await ctx.send(f"The {role.name} role has been removed.")
                else:
                    roles.append(role.id)
                    await ctx.send(f"The {role.name} role has been added.")
        else:
            roles = await self.conf.guild(ctx.guild).roles()
            new = copy.deepcopy(roles)
            if not roles:
                await ctx.send("No roles are set for ping right now.")
                return
            e = discord.Embed(
                title="The following roles are pinged when a report comes in.", description=""
            )
            for r in roles:
                ro = ctx.guild.get_role(r)
                if ro:
                    e.description += ro.mention + "\n"
                else:
                    new.remove(r)
            if new != roles:
                await self.conf.guild(ctx.guild).roles.set(new)
            await ctx.send(embed=e)

    @commands.is_owner()
    @scanner.command()
    async def creds(self, ctx, user, secret):
        """Set the API user and API secret to use with requests from sightengine.com."""
        await self.conf.userkey.set(user)
        await self.conf.secret.set(secret)
        await ctx.tick()

    @scanner.command()
    async def settings(self, ctx):
        """View registered settings"""
        settings = await self.conf.guild(ctx.guild).all()
        channel = self.bot.get_channel(settings["channel"])
        whitelist = [
            self.bot.get_channel(c).mention
            for c in settings["whitelist"]
            if self.bot.get_channel(c)
        ] or ["`None`"]
        blacklist = [
            self.bot.get_channel(c).mention
            for c in settings["blacklist"]
            if self.bot.get_channel(c)
        ] or ["`None`"]
        s = (
            f"Reporting Channel: {channel.mention if channel else '`None`'}\n"
            f"Whitelisted Channels: {humanize_list(whitelist)}\n"
            f"Blacklisted Channels: {humanize_list(blacklist)}\n"
            "```py\n"
            f"Percent: {settings['percent']}\n"
            f"Auto Deleting: {settings['autodelete']}\n"
            f"Checking for Nudes: {settings['nude']}\n"
            f"Checking for Partials: {settings['partial']}\n"
            f"Checking for WAD: {settings['wad']}\n"
            f"Checking for Offensive: {settings['offensive']}\n"
            f"Checking for Scammers: {settings['scammer']}\n"
            f"Checking for Text Moderation: Use {ctx.prefix}scanner detect tm\n"
            f"Checking for Message moderation: Use {ctx.prefix}scanner detect mm\n"
            "```"
        )
        await ctx.send(s)

    @scanner.group()
    async def lists(self, ctx):
        """Manage whitelist and blacklists for Scanner cog."""
        pass

    @lists.group()
    async def whitelist(self, ctx):
        """Whitelist channels from the scanner.

        Whitelisted channels will be the ONLY channels checked for rule violating pictures"""
        pass

    @whitelist.command(name="add")
    async def whitelistadd(self, ctx, *channels: discord.TextChannel):
        """Add channels to the whitelist"""
        data = await self.conf.guild(ctx.guild).whitelist()
        ds = set(data)
        ns = set([c.id for c in channels])
        ss = ds | ns
        await self.conf.guild(ctx.guild).whitelist.set(list(ss))
        ss = [self.bot.get_channel(c).mention for c in list(ss) if self.bot.get_channel(c)] or [
            "`None`"
        ]
        await ctx.send(f"Whitelist update successful: {humanize_list(ss)}")

    @whitelist.command(name="remove")
    async def whitelistremove(self, ctx, *channels: discord.TextChannel):
        """Remove channels from the whitelist"""
        data = await self.conf.guild(ctx.guild).whitelist()
        ds = set(data)
        ns = set([c.id for c in channels])
        ss = ds - ns
        await self.conf.guild(ctx.guild).whitelist.set(list(ss))
        ss = [self.bot.get_channel(c).mention for c in list(ss) if self.bot.get_channel(c)] or [
            "`None`"
        ]
        await ctx.send(f"Whitelist update successful: {humanize_list(ss)}")

    @whitelist.command(name="clear")
    async def whitelistclear(self, ctx):
        """Removes all channels from the whitelist"""
        await self.conf.guild(ctx.guild).whitelist.set([])
        await ctx.send("Whitelist update successful")

    @lists.group()
    async def blacklist(self, ctx):
        """Blacklist channels from the scanner.

        Blacklisted channels will NOT be checked for rule-violating pictures."""
        pass

    @blacklist.command(name="add")
    async def blacklistadd(self, ctx, *channels: discord.TextChannel):
        """Add channels to the blacklist"""
        data = await self.conf.guild(ctx.guild).blacklist()
        ds = set(data)
        ns = set([c.id for c in channels])
        ss = ds | ns
        await self.conf.guild(ctx.guild).blacklist.set(list(ss))
        ss = [self.bot.get_channel(c).mention for c in list(ss) if self.bot.get_channel(c)] or [
            "`None`"
        ]
        await ctx.send(f"Blacklist update successful: {humanize_list(ss)}")

    @blacklist.command(name="remove")
    async def blacklistremove(self, ctx, *channels: discord.TextChannel):
        """Remove channels from the blacklist"""
        data = await self.conf.guild(ctx.guild).blacklist()
        ds = set(data)
        ns = set([c.id for c in channels])
        ss = ds - ns
        await self.conf.guild(ctx.guild).blacklist.set(list(ss))
        ss = [self.bot.get_channel(c).mention for c in list(ss) if self.bot.get_channel(c)] or [
            "`None`"
        ]
        await ctx.send(f"Blacklist update successful: {humanize_list(ss)}")

    @blacklist.command(name="clear")
    async def blacklistclear(self, ctx):
        """Removes all channels from the blacklist"""
        await self.conf.guild(ctx.guild).blacklist.set([])
        await ctx.send("Blacklist update successful")

    @scanner.group()
    async def detect(self, ctx):
        """Group command for changing what the scanner cog detects."""
        pass

    @detect.command()
    async def nude(self, ctx, yes_or_no: bool):
        """Set whether or not to check for nude content in images."""
        await self.conf.guild(ctx.guild).nude.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Messages will now be reported if they violate the nude rule.")
        else:
            await ctx.send("Messages will now not be reported even if they violate the nude rule.")

    @detect.command()
    async def partial(self, ctx, yes_or_no: bool):
        """Set whether or not messages will be reported be they contain partial nudity.

        Note that the nude toggle must be turned on for this to work."""
        await self.conf.guild(ctx.guild).partial.set(yes_or_no)
        if yes_or_no:
            await ctx.send(
                "Messages will now be reported if they are marked as a having partial nudity."
            )
        else:
            await ctx.send(
                "Messages will now not be reported even if they are marked as having partial nudity."
            )

    @detect.command()
    async def wad(self, ctx, yes_or_no: bool):
        """Set whether or not to check for WAD content in images.

        WAD stands for Weapons, Alcohol and Drugs"""
        await self.conf.guild(ctx.guild).wad.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Messages will now be reported if they violate the WAD rule.")
        else:
            await ctx.send("Messages will now not be reported even if they violate the WAD rule.")

    @detect.command()
    async def offensive(self, ctx, yes_or_no: bool):
        """Set whether or not to check for offensive content in images.

        Offensive content includes content such as middle fingers, offensive flags or offensive groups of people.
        """
        await self.conf.guild(ctx.guild).offensive.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Messages will now be reported if they violate the offensive rule.")
        else:
            await ctx.send(
                "Messages will now not be reported even if they violate the offensive rule."
            )

    @detect.command()
    async def scammer(self, ctx, yes_or_no: bool):
        """Set whether or not to check for scammer content in images.

        By scammer content it checks for verified scammers in the picture."""
        await self.conf.guild(ctx.guild).scammer.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Messages will now be reported if they violate the scammer rule.")
        else:
            await ctx.send(
                "Messages will now not be reported even if they violate the scammer rule."
            )

    @detect.group(aliases=["textmoderation"], invoke_without_command=True)
    async def tm(self, ctx):
        """Manage settings for Text Moderation in pictures."""
        data = await self.conf.guild(ctx.guild).textmoderation()
        await ctx.send(
            (
                "```"
                f"Text Moderation Enabled: {data['enabled']}\n"
                f"Text Moderation Checks: {humanize_list(data['checks'])}\n"
                "```"
            )
        )

    @tm.group(name="checks")
    async def checks_command(self, ctx):
        """Manage the various profanities to check for in Text Moderation in images."""
        pass

    @checks_command.command(name="add")
    async def checks_add(self, ctx, *checks: str):
        """Adds checks to the Text Moderation check.

        Must be `sexual`, `insult`, `disciminatory`, `innapropriate`, `other_profanity`, `email`, `ipv4`, `ipv6`, `phone_number_us`, `phone_number_uk`, `phone_number_fr` or `ssn`.
        """
        if not checks:
            return await ctx.send_help()
        data = await self.conf.guild(ctx.guild).textmoderation()
        pc = set(data["checks"])
        nc = set([check.lower() for check in checks])

        for check in nc:
            if check not in TEXT_MODERATION_CHECKS:
                await ctx.send(f"Unrecognized check: `{check}`")
                return

        sc = list(pc | nc)
        data["checks"] = sc
        await self.conf.guild(ctx.guild).textmoderation.set(data)
        await ctx.send(
            f"Text moderation check update successful: {humanize_list(list(map(inline, sc)))}"
        )

    @checks_command.command(name="remove")
    async def checks_remove(self, ctx, *checks: str):
        """Removes checks from the Text Moderation check"""
        if not checks:
            return await ctx.send_help()
        data = await self.conf.guild(ctx.guild).textmoderation()
        pc = set(data["checks"])
        nc = set([check.lower() for check in checks])

        for check in nc:
            if check not in TEXT_MODERATION_CHECKS:
                await ctx.send(f"Unrecognized check: `{check}`")
                return

        sc = list(pc - nc)
        data["checks"] = sc
        await self.conf.guild(ctx.guild).textmoderation.set(data)
        await ctx.send(
            f"Text moderation check update successful: {humanize_list(list(map(inline, sc)))}"
        )

    @checks_command.command(name="clear")
    async def checks_clear(self, ctx):
        """Removes all channels from the whitelist"""
        async with self.conf.guild(ctx.guild).textmoderation() as data:
            data["checks"] = []
        await ctx.send("Text moderation check update successful")

    @tm.command(name="enable")
    async def textmoderation_enable(self, ctx, yes_or_no: bool):
        """Set whether or not to check for Text Mderation in images."""
        async with self.conf.guild(ctx.guild).textmoderation() as data:
            data["enabled"] = yes_or_no
        if yes_or_no:
            await ctx.send(
                "Messages will now be reported if they violate the Text Moderation checks.\nThis may make image processing slower, due to having to scan the image for additional text."
            )
        else:
            await ctx.send(
                "Messages will now not be reported even if they violate the Text Moderation checks."
            )

    # -----------------------------------------------------

    @detect.group(aliases=["messagemoderation"], invoke_without_command=True)
    async def mm(self, ctx):
        """Manage settings for Message Moderation."""
        data = await self.conf.guild(ctx.guild).rawtextmoderation()
        await ctx.send(
            (
                "```"
                f"Message Moderation Enabled: {data['enabled']}\n"
                f"Message Moderation Language: {data['lang']}\n"
                f"Message Moderation Checks: {humanize_list(data['checks'])}\n"
                "```"
            )
        )

    @mm.group(name="checks")
    async def mm_checks_command(self, ctx):
        """Manage the various types to check for in Message Moderation."""
        pass

    @mm_checks_command.command(name="add")
    async def mm_checks_add(self, ctx, *checks: str):
        """Adds checks to the Message Moderation check.

        Must be `sexual`, `insult`, `disciminatory`, `innapropriate`, `other_profanity`, `email`, `ipv4`, `ipv6`, `phone_number_us`, `phone_number_uk`, `phone_number_fr` or `ssn`.
        """
        if not checks:
            return await ctx.send_help()
        data = await self.conf.guild(ctx.guild).rawtextmoderation()
        pc = set(data["checks"])
        nc = set([check.lower() for check in checks])

        for check in nc:
            if check not in TEXT_MODERATION_CHECKS:
                await ctx.send(f"Unrecognized check: `{check}`")
                return

        sc = list(pc | nc)
        data["checks"] = sc
        await self.conf.guild(ctx.guild).rawtextmoderation.set(data)
        await ctx.send(
            f"Message moderation check update successful: {humanize_list(list(map(inline, sc)))}"
        )

    @mm_checks_command.command(name="remove")
    async def mm_checks_remove(self, ctx, *checks: str):
        """Removes checks from the Message Moderation check"""
        if not checks:
            return await ctx.send_help()
        data = await self.conf.guild(ctx.guild).rawtextmoderation()
        pc = set(data["checks"])
        nc = set([check.lower() for check in checks])

        for check in nc:
            if check not in TEXT_MODERATION_CHECKS:
                await ctx.send(f"Unrecognized check: `{check}`")
                return

        sc = list(pc - nc)
        data["checks"] = sc
        await self.conf.guild(ctx.guild).rawtextmoderation.set(data)
        await ctx.send(
            f"Message moderation check update successful: {humanize_list(list(map(inline, sc)))}"
        )

    @mm_checks_command.command(name="clear")
    async def mm_checks_clear(self, ctx):
        """Removes all checks from Message Moderation"""
        async with self.conf.guild(ctx.guild).rawtextmoderation() as data:
            data["checks"] = []
        await ctx.send("Message moderation check update successful")

    @commands.is_owner()
    @mm.command(name="enable")
    async def messagemoderation_enable(self, ctx, yes_or_no: bool):
        """Set whether or not to check for Message Mderation."""
        async with self.conf.guild(ctx.guild).rawtextmoderation() as data:
            data["enabled"] = yes_or_no
        if yes_or_no:
            await ctx.send(
                "Messages will now be reported if they violate the MessageModeration checks.\nThis will make your bot slower and will use up your API quota fast!  Be aware of issues that may arise due to this."
            )
        else:
            await ctx.send(
                "Messages will now not be reported even if they violate the Message Moderation checks."
            )
