from redbot.core import commands, checks, Config
import discord
import typing
import asyncio


OWNER = discord.PermissionOverwrite(
    manage_permissions=True,
    manage_channels=True,
    connect=True,
    speak=True,
    stream=True,
    mute_members=True,
    deafen_members=True,
    move_members=True,
)

HOST = discord.PermissionOverwrite(connect=True, speak=True, stream=True)

BASE = discord.PermissionOverwrite(connect=True, speak=False, stream=False)


class EventVC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=473541068378341376)

        default_guild = {
            # Announcement settings
            "announcechannel": 0,
            "announcerole": 0,
            # Creation settings
            "eventhostrole": 0,
            "eventcategory": 0,
            "eventlogging": 0,
            "created": {},
        }
        self.config.register_guild(**default_guild)

    # Settings
    @checks.admin()
    @commands.command()
    async def eventchannel(self, ctx, channel: discord.TextChannel):
        """Set the channel to put Event Creation announcements in"""
        await self.config.guild(ctx.guild).announcechannel.set(channel.id)
        await ctx.send(f"Event creation messages will now be sent to {channel.mention}.")

    @checks.admin()
    @commands.command()
    async def eventroletag(self, ctx, role: discord.Role):
        """Set the role to be pinged when a new Event is created."""
        await self.config.guild(ctx.guild).announcerole.set(role.id)
        await ctx.send(f"Event creation messages will now tag the role {role.mention}.")

    @checks.admin()
    @commands.command()
    async def eventcategory(self, ctx, channel: discord.CategoryChannel):
        """Set the category for Event VCs to be created under."""
        await self.config.guild(ctx.guild).eventcategory.set(channel.id)
        await ctx.send(f"Event VCs will now be created under the category {str(channel)}.")

    @checks.admin()
    @commands.command()
    async def eventhostrole(self, ctx, role: discord.Role):
        """Set the role that can create Events and have Speak permission
        in other Events"""
        await self.config.guild(ctx.guild).eventhostrole.set(role.id)
        await ctx.send(
            f"Event VCs now can be created and spoken in by users in the role {role.mention}."
        )

    @checks.admin()
    @commands.command()
    async def eventlogging(self, ctx, channel: discord.TextChannel):
        """Set the channel to put Event command logging in"""
        await self.config.guild(ctx.guild).eventlogging.set(channel.id)
        await ctx.send(f"Event commands will now be logged in {channel.mention}.")

    # User commands

    @commands.command()
    async def eventcreate(self, ctx, *, name):
        """Create an Event"""
        guild_settings = await self.config.guild(ctx.guild).all()
        if guild_settings["eventhostrole"] == 0:
            await ctx.send(
                f"Event setup not complete.  Please have an admin run `{ctx.prefix}eventhostrole`."
            )
            return

        if guild_settings["eventhostrole"] not in [role.id for role in ctx.author.roles]:
            await ctx.send("You are not authorized to create Events.")
            return

        if len(name) > 100:
            await ctx.send("Event VCs cannot have names larger than 100 characters.")

        if guild_settings["eventcategory"] == 0 or not (
            category := ctx.guild.get_channel(guild_settings["eventcategory"])
        ):
            await ctx.send(
                f"Event setup not complete.  Please have an admin run `{ctx.prefix}eventcategory`."
            )
            return

        if not category.permissions_for(ctx.me).manage_channels:
            await ctx.send(
                "Event setup not complete.  Please allow me "
                "Manage Channels permission in set category."
            )
            return

        for event in guild_settings["created"]:
            if ctx.author.id == event["host"]:
                await ctx.send("You cannot create another event while you have one running!")
                return

        overwrites = {
            ctx.author: OWNER,
            ctx.me: OWNER,
            ctx.guild.get_role(guild_settings["eventhostrole"]): HOST,
            ctx.guild.default_role: BASE,
        }

        created = await category.create_voice_channel(name, overwrites=overwrites)
        if announce := ctx.guild.get_channel(guild_settings["announcechannel"]):
            embed = discord.Embed(
                title="A new Event has been created!", color=await ctx.embed_color()
            )
            embed.add_field(name="Author", value=f"{str(ctx.author)}")
            embed.add_field(name="Channel", value=f"{str(created)}")

            if announce_role := ctx.guild.get_role(guild_settings["announcerole"]):
                content = announce_role.mention
            else:
                content = ""

            await announce.send(
                content=content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=True),
            )

        if logging := ctx.guild.get_channel(guild_settings["eventlogging"]):
            embed = discord.Embed(
                title="",
                description=f"**{str(ctx.author)}** used `{ctx.prefix}eventcreate`.",
                color=await ctx.embed_color(),
            )
            await logging.send(embed=embed)

        async with self.config.guild(ctx.guild).created() as events:
            events[str(created.id)] = {"host": ctx.author.id, "hosts": []}

        await ctx.send("Your Event has successfully been created!")

    @commands.command()
    async def eventdelete(
        self, ctx, *, channel: typing.Optional[typing.Union[discord.VoiceChannel, int]] = None
    ):
        """Delete an Event, removing the channel and from the bot."""
        existing = await self.config.guild(ctx.guild).created()
        if channel:
            if isinstance(channel, int):
                channel = ctx.guild.get_channel(channel) or channel
            try:
                event = existing[
                    str(channel.id) if isinstance(channel, discord.VoiceChannel) else str(channel)
                ]
            except KeyError:
                await ctx.send("Could not find an Event registered under that channel.")
                return
            if (
                ctx.author.id != event["host"]
                and ctx.author.id not in event["hosts"]
                and ctx.author.id != ctx.guild.owner_id
            ):
                await ctx.send("You are not a Host/Co-Host of that Event!")
                return
            event_id = channel.id if isinstance(channel, discord.VoiceChannel) else channel
        else:
            event = None
            for (event_id, event_temp) in existing.items():
                if event_temp["host"] == ctx.author.id:
                    channel = ctx.guild.get_channel(int(event_id))
                    event = event_temp
                    break

            if not event:
                await ctx.send(
                    "Failed to find an Event you are Hosting.  "
                    "If you are Co-Hosting, please specify the channel."
                )
                return

        representing_channel = str(channel) if channel else event_id
        representing_host = ctx.guild.get_member(event["host"]) or event["host"]

        await ctx.send(
            f"You are about to delete the Event tied to channel {representing_channel}, "
            f"hosted by {representing_host}.  Are you sure you want to do this?  "
            "Type 'yes' to confirm."
        )

        def check(m):
            return (
                m.channel.id == ctx.channel.id
                and m.author.id == ctx.author.id
                and m.content.lower() in ["yes", "no"]
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("Cancelled.")
            return

        if msg.content.lower() == "yes":
            if channel:
                try:
                    await channel.delete()
                except discord.HTTPException:
                    await ctx.send(
                        "I was unable to delete the corresponding channel.  Continuing..."
                    )

            eventlogging = await self.config.guild(ctx.guild).eventlogging()
            if logging := ctx.guild.get_channel(eventlogging):
                embed = discord.Embed(
                    title="",
                    description=(
                        f"**{str(ctx.author)}** used `{ctx.prefix}eventdelete` "
                        f"on channel **{representing_channel}**."
                    ),
                    color=await ctx.embed_color(),
                )
                await logging.send(embed=embed)

            async with self.config.guild(ctx.guild).created() as events:
                del events[str(event_id)]

            await ctx.send("Event has been deleted.")
        else:
            await ctx.send("Cancelled.")

    @commands.command()
    async def eventcohost(self, ctx, *, user: discord.Member):
        """Add a user as a Co-Host to your Event.  This is non-reversable!"""
        existing = await self.config.guild(ctx.guild).created()
        event = None
        for (event_id, event_temp) in existing.items():
            if event_temp["host"] == ctx.author.id:
                channel = ctx.guild.get_channel(int(event_id))
                event = event_temp
                break

        if not event:
            await ctx.send("Could not find an event that you are Hosting!")
            return

        if not channel:
            await ctx.send("The channel linked to your Event has been deleted!")
            return

        if user.id in event["hosts"]:
            await ctx.send("That user is already a Co-Host!")
            return

        if user.id == ctx.author.id:
            await ctx.send("You cannot add yourself as a Co-Host!")
            return

        await ctx.send(
            f"You are about to add {str(user)} as a Co-Host to your Event.  "
            "They will have full permissions (besides adding Co-Hosts), and cannot be removed.  "
            "Are you sure you want to do this?  Type 'yes' to confirm."
        )

        def check(m):
            return (
                m.channel.id == ctx.channel.id
                and m.author.id == ctx.author.id
                and m.content.lower() in ["yes", "no"]
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("Cancelled.")
            return

        if msg.content.lower() == "yes":
            async with self.config.guild(ctx.guild).created() as events:
                events[str(channel.id)]["hosts"].append(user.id)

            await channel.set_permissions(user, overwrite=OWNER)

            eventlogging = await self.config.guild(ctx.guild).eventlogging()
            if logging := ctx.guild.get_channel(eventlogging):
                embed = discord.Embed(
                    title="",
                    description=(
                        f"**{str(ctx.author)}** used `{ctx.prefix}eventcohost` "
                        f"on channel **{str(channel)}** with user **{str(user)}**."
                    ),
                    color=await ctx.embed_color(),
                )
                await logging.send(embed=embed)

            await ctx.send(f"{str(user)} has been added as a Co-Host.")
        else:
            await ctx.send("Cancelled.")

    @commands.command()
    async def eventrename(
        self,
        ctx,
        channel: typing.Optional[typing.Union[discord.VoiceChannel, int]] = None,
        *,
        name,
    ):
        """Rename the channel created with your Event"""
        existing = await self.config.guild(ctx.guild).created()
        if channel:
            if isinstance(channel, int):
                channel = ctx.guild.get_channel(channel)
                if not channel:
                    await ctx.send("Could not find that channel!")
                    return
            try:
                event = existing[str(channel.id)]
            except KeyError:
                await ctx.send("Could not find an Event registered under that channel.")
                return
            if (
                ctx.author.id != event["host"]
                and ctx.author.id not in event["hosts"]
                and ctx.author.id != ctx.guild.owner_id
            ):
                await ctx.send("You are not a Host/Co-Host of that Event!")
                return
        else:
            for (event_id, event_temp) in existing.items():
                if event_temp["host"] == ctx.author.id:
                    channel = ctx.guild.get_channel(int(event_id))
                    if not channel:
                        await ctx.send("Your Event channel no longer exists!")
                        return
                    break

            if not channel:
                await ctx.send(
                    "Failed to find an Event you are Hosting.  "
                    "If you are Co-Hosting, please specify the channel before the new name."
                )
                return
        await channel.edit(name=name)

        eventlogging = await self.config.guild(ctx.guild).eventlogging()
        if logging := ctx.guild.get_channel(eventlogging):
            embed = discord.Embed(
                title="",
                description=(
                    f"**{str(ctx.author)}** used `{ctx.prefix}eventrename` "
                    f"on channel {str(channel)}."
                ),
                color=await ctx.embed_color(),
            )
            await logging.send(embed=embed)

        await ctx.send("The Event channel's name has been updated.")
