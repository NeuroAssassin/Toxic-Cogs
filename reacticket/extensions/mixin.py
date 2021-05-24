from redbot.core import commands, checks


@checks.bot_has_permissions(add_reactions=True)
@commands.guild_only()
@commands.group(name="reacticket")
async def reacticket(self, ctx: commands.Context):
    """Create a reaction ticket system in your server"""
    pass


@checks.admin()
@reacticket.group(invoke_without_command=True, aliases=["set"])
async def settings(self, ctx):
    """Manage settings for ReacTicket"""
    await ctx.send_help()
    guild_settings = await self.config.guild(ctx.guild).all()
    channel_id, message_id = list(map(int, guild_settings["msg"].split("-")))

    ticket_channel = getattr(self.bot.get_channel(channel_id), "name", "Not set")
    ticket_category = getattr(self.bot.get_channel(guild_settings["category"]), "name", "Not set")
    archive_category = getattr(
        self.bot.get_channel(guild_settings["archive"]["category"]), "name", "Not set"
    )
    report_channel = getattr(self.bot.get_channel(guild_settings["report"]), "name", "Not set")

    await ctx.send(
        "```ini\n"
        f"[Ticket Channel]:    {ticket_channel}\n"
        f"[Ticket MessageID]:  {message_id}\n"
        f"[Ticket Reaction]:   {guild_settings['reaction']}\n"
        f"[User-closable]:     {guild_settings['usercanclose']}\n"
        f"[User-modifiable]:   {guild_settings['usercanmodify']}\n"
        f"[User-nameable]:     {guild_settings['usercanclose']}\n"
        f"[Ticket Category]:   {ticket_category}\n"
        f"[Report Channel]:    {report_channel}\n"
        f"[Ticket Close DM]:   {guild_settings['dm']}\n"
        f"[Archive Category]:  {archive_category}\n"
        f"[Archive Enabled]:   {guild_settings['archive']['enabled']}\n"
        f"[System Enabled]:    {guild_settings['enabled']}\n"
        "```"
    )


class RTMixin:
    """ This is mostly here to easily mess with things... """

    c = reacticket
    s = settings
