from redbot.core import commands, Config, checks
import discord
import aiohttp
import contextlib
import io
import traceback

URL = "https://api.sightengine.com/1.0/check.json"


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
            "channel": 0,
            "percent": 70,
            "autodelete": True,
        }
        self.conf.register_guild(**default_guild)
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.session.detach()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return
        try:
            if not message.guild:
                return
            if not message.attachments:
                return

            user = await self.conf.userkey()
            if user == "":
                return
            secret = await self.conf.secret()
            if secret == "":
                return

            settings = await self.conf.guild(message.guild).all()
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
            if s == "":
                return
            s = s[:-1]  # Remove the extra ,

            for attach in message.attachments:
                nudity = False
                partial = False
                wad = False
                offensive = False
                scammer = False
                params = {"models": s, "url": attach.url, "api_user": user, "api_secret": secret}
                returned = await self.session.get(URL, params=params)
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
                if nudity or partial or wad or offensive or scammer:
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
                            else ""
                        )
                        embed.add_field(name="Violating:", value=violating)
                        if not deleted:
                            embed.add_field(
                                name="Message was not deleted",
                                value=f"Here's a jump url: [Click Here]({message.jump_url})",
                            )
                        await channel.send(embed=embed, file=f)
        except Exception as error:
            await message.channel.send("Error")
            await message.channel.send(
                "".join(traceback.format_exception(type(error), error, error.__traceback__))
            )

    @checks.admin_or_permissions(manage_messages=True)
    @commands.group()
    async def scanner(self, ctx):
        """Group command for changing scanner's settings."""
        pass

    @scanner.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set the channel for reports to go to."""
        await self.conf.guild(ctx.guild).channel.set(channel.id)
        await ctx.tick()

    @scanner.command()
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

    @scanner.command()
    async def percent(self, ctx, percent: int):
        """Set the percent a picture must have in order to be violating.  100 means full violation, 0 is no violation"""
        if percent < 1 or percent > 100:
            return await ctx.send("Must be between 1 and 100")
        await self.conf.guild(ctx.guild).percent.set(percent)

    @checks.is_owner()
    @scanner.command()
    async def creds(self, ctx, user, secret):
        """Set the API user and API secret to use with requests."""
        await self.conf.userkey.set(user)
        await self.conf.secret.set(secret)
        await ctx.tick()

    @scanner.group(invoke_without_command=True)
    async def settings(self, ctx):
        """Group command for setting what filters to look for."""
        settings = await self.conf.guild(ctx.guild).all()
        channel = self.bot.get_channel(settings["channel"])
        s = (
            f"Channel: {channel.mention if channel else 'None set'}\n"
            f"Percent: {settings['percent']}\n"
            f"Auto Deleting: {settings['autodelete']}\n"
            f"Checking for Nudes: {settings['nude']}\n"
            f"Checking for Partials: {settings['partial']}\n"
            f"Checking for WAD: {settings['wad']}\n"
            f"Checking for Offensive: {settings['offensive']}\n"
            f"Checking for Scammers: {settings['scammer']}\n"
        )
        await ctx.send("```" + s + "```")

    @settings.command()
    async def nude(self, ctx, yes_or_no: bool):
        """Set whether or not to check for nude content in images."""
        await self.conf.guild(ctx.guild).nude.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Messages will now be reported if they violate the nude rule.")
        else:
            await ctx.send("Messages will now not be reported even if they violate the nude rule.")

    @settings.command()
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

    @settings.command()
    async def wad(self, ctx, yes_or_no: bool):
        """Set whether or not to check for WAD content in images.

        WAD stands for Weapons, Alcohol and Drugs"""
        await self.conf.guild(ctx.guild).wad.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Messages will now be reported if they violate the WAD rule.")
        else:
            await ctx.send("Messages will now not be reported even if they violate the WAD rule.")

    @settings.command()
    async def offensive(self, ctx, yes_or_no: bool):
        """Set whether or not to check for offensive content in images.

        Offensive content includes content such as middle fingers, offensive flags or offensive groups of people."""
        await self.conf.guild(ctx.guild).offensive.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Messages will now be reported if they violate the offensive rule.")
        else:
            await ctx.send(
                "Messages will now not be reported even if they violate the offensive rule."
            )

    @settings.command()
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
