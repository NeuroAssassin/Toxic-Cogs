# Huge thanks to Sinbad for allowing me to copy parts of his RSS cog, which I used to grab the latest commits from repositories.

# Also, the code I use for updating repos I took directly from Red, and just took out the message interactions

from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import humanize_list, inline
import asyncio
import aiohttp
import feedparser
import discord
import traceback
from typing import Optional
from datetime import datetime


class UpdateChecker(commands.Cog):
    """Get notices or auto-update cogs when an update is available for it's repo"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.conf = Config.get_conf(self, identifier=473541068378341376)
        default_global = {
            "updated": False,
            "repos": {},
            "auto": False,
            "gochannel": 0,
            "embed": True,
        }
        self.conf.register_global(**default_global)
        self.task = self.bot.loop.create_task(self.bg_task())

    def cog_unload(self):
        self.__unload()

    def __unload(self):
        self.task.cancel()
        self.session.detach()

    async def bg_task(self):
        await self.bot.wait_until_ready()
        # Just in case
        await asyncio.sleep(10)
        while True:
            updated = await self.conf.updated()
            if updated:
                cog = self.bot.get_cog("Downloader")
                if cog != None:
                    repos = await self.conf.repos()
                    auto = await self.conf.auto()
                    channel = await self.conf.gochannel()
                    use_embed = await self.conf.embed()
                    if channel == 0:
                        channel = (await self.bot.application_info()).owner
                    else:
                        channel = self.bot.get_channel(channel)
                    all_repos = cog._repo_manager.get_all_repo_names()
                    for repo in all_repos:
                        if not (repo in list(repos.keys())):
                            repos[repo] = "--default--"
                            await self.conf.repos.set(repos)
                    saving_dict = {k: v for k, v in repos.items() if k in all_repos}
                    for repo_name, commit_saved in saving_dict.items():
                        repo = cog._repo_manager.get_repo(repo_name)
                        if not repo:
                            continue
                        url = repo.url + r"/commits/" + repo.branch + ".atom"
                        response = await self.fetch_feed(url)
                        try:
                            commit = response.entries[0]["title"]
                        except AttributeError:
                            continue
                        saving_dict[repo_name] = commit
                        if commit != commit_saved and commit_saved != "--default--":
                            if not auto:
                                if (
                                    use_embed
                                    and channel.permissions_for(channel.guild.me).embed_links
                                ):
                                    e = discord.Embed(
                                        title="[Update Checker]",
                                        description=f"Update available for repo: {repo.name}",
                                        timestamp=datetime.utcnow(),
                                        color=0x00FF00,
                                    )
                                    e.add_field(name="URL", value=repo.url)
                                    e.add_field(name="Branch", value=repo.branch)
                                    e.add_field(name="Commit", value=commit)
                                else:
                                    message = (
                                        "```css\n"
                                        "[Update Checker]"
                                        "``````css\n"
                                        f"    Repo: {repo.name}\n"
                                        f"     URL: {repo.url}\n"
                                        f"  Commit: {commit}\n"
                                        f"    Time: {datetime.utcnow()}"
                                        "```"
                                    )
                                try:
                                    if (
                                        use_embed
                                        and channel.permissions_for(channel.guild.me).embed_links
                                    ):
                                        await channel.send(embed=e)
                                    else:
                                        await channel.send(message)
                                except AttributeError:
                                    owner = (await self.bot.application_info()).owner
                                    await owner.send(
                                        "[Update Checker] It appears that the channel for this cog has been deleted.  From now on, it will DM you."
                                    )
                                    if use_embed:
                                        await owner.send(embed=e)
                                    else:
                                        await channel.send(message)
                                    channel = owner
                                    await self.conf.gochannel.set(0)
                                except discord.errors.Forbidden:
                                    owner = (await self.bot.application_info()).owner
                                    await owner.send(
                                        "[Update Checker] It appears that I am no longer allowed to send messages to the designated update channel.  From now on, it will DM you."
                                    )
                                    channel = owner
                                    await self.conf.gochannel.set(0)
                            else:
                                try:
                                    await channel.send(
                                        f"[Update Checker] Update found for repo: {repo.name}.  Updating repos..."
                                    )
                                except AttributeError:
                                    owner = (await self.bot.application_info()).owner
                                    await owner.send(
                                        "[Update Checker] It appears that the channel for this cog has been deleted.  From now on, it will DM you."
                                    )
                                    channel = owner
                                    await self.conf.gochannel.set(0)
                                except discord.errors.Forbidden:
                                    owner = (await self.bot.application_info()).owner
                                    await owner.send(
                                        "[Update Checker] It appears that I am no longer allowed to send messages to the designated update channel.  From now on, it will DM you."
                                    )
                                    channel = owner
                                    await self.conf.gochannel.set(0)
                                # Just a copy of `[p]cog update`, but without using ctx things
                                try:
                                    installed_cogs = set(await cog.installed_cogs())
                                    updated = await cog._repo_manager.update_all_repos()
                                    updated_cogs = set(
                                        cog for repo in updated for cog in repo.available_cogs
                                    )
                                    installed_and_updated = updated_cogs & installed_cogs
                                    if installed_and_updated:
                                        await cog._reinstall_requirements(installed_and_updated)
                                        await cog._reinstall_cogs(installed_and_updated)
                                        await cog._reinstall_libraries(installed_and_updated)
                                        cognames = {c.name for c in installed_and_updated}
                                        message = humanize_list(tuple(map(inline, cognames)))
                                except Exception as error:
                                    exception_log = (
                                        "Exception while updating repos in Update Checker \n"
                                    )
                                    exception_log += "".join(
                                        traceback.format_exception(
                                            type(error), error, error.__traceback__
                                        )
                                    )
                                    try:
                                        await channel.send(
                                            f"[Update Checker]: Error while updating repos.\n\n{exception_log}"
                                        )
                                    except discord.errors.Forbidden:
                                        pass
                                else:
                                    try:
                                        await channel.send(
                                            f"[Update Checker]: Ran cog update.  Updated cogs: {message}"
                                        )
                                    except discord.errors.Forbidden:
                                        pass
                    await self.conf.repos.set(saving_dict)
            await asyncio.sleep(60)

    async def fetch_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        # Thank's to Sinbad's rss cog after which I copied this
        timeout = aiohttp.client.ClientTimeout(total=15)
        try:
            async with self.session.get(url, timeout=timeout) as response:
                data = await response.read()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None

        ret = feedparser.parse(data)
        if ret.bozo:
            return None
        return ret

    @checks.is_owner()
    @commands.group(name="cogupdater")
    async def update(self, ctx):
        """Group command for controlling the update checker cog."""
        pass

    @checks.is_owner()
    @update.command()
    async def auto(self, ctx):
        """Changes automatic cog updates to the opposite setting."""
        auto = await self.conf.auto()
        await self.conf.auto.set(not auto)
        status = "disabled" if auto else "enabled"
        await ctx.send(f"Auto cog updates are now {status}")

    @checks.is_owner()
    @update.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """Sets a channel for update messages to go to.

        If argument is not supplied, it will be sent to the bot owner's DMs.  By default, goes to owner DMs."""
        if channel:
            await self.conf.gochannel.set(channel.id)
            await ctx.send(f"Update messages will now be sent to {channel.mention}")
        else:
            await self.conf.gochannel.set(0)
            await ctx.send("Update messages will now be DMed to you.")

    @checks.is_owner()
    @update.command()
    async def settings(self, ctx):
        """See settings for the Update Checker cog.

        Right now, this shows whether the bot updates cogs automatically and what channel logs are sent to."""
        auto = await self.conf.auto()
        channel = await self.conf.gochannel()
        embed = await self.conf.embed()
        if embed:
            e = discord.Embed(title="Update Checker settings", color=0x00FF00)
            e.add_field(name="Automatic Cog Updates", value=str(auto))
            if channel == 0:
                channel = "Direct Messages"
            else:
                try:
                    channel = self.bot.get_channel(channel).name
                except:
                    channel = "Unknown"
            e.add_field(name="Update Channel", value=channel)
            await ctx.send(embed=e)
        else:
            if channel == 0:
                channel = "Direct Messages"
            else:
                try:
                    channel = self.bot.get_channel(channel).name
                except:
                    channel = "Unknown"
            message = (
                "```css\n"
                "[Update Checker settings]"
                "``````css\n"
                f"[Automatic Cog Updates]: {str(auto)}\n"
                f"       [Update Channel]: {channel}"
                "```"
            )
            await ctx.send(message)

    @checks.is_owner()
    @update.command()
    async def embed(self, ctx):
        """Toggles whether to use embeds or colorful codeblock messages when sending an update."""
        c = await self.conf.embed()
        await self.conf.embed.set(not c)
        word = "disabled" if c else "enabled"
        await ctx.send(f"Embeds are now {word}")

    @checks.is_owner()
    @update.group(name="task", hidden=True)
    async def _group_update_task(self, ctx):
        """View the status of the task (the one checking for updates)."""
        pass

    @_group_update_task.command()
    async def status(self, ctx):
        """Get the current status of the update task."""
        message = "Task is currently "
        cancelled = self.task.cancelled()
        if cancelled:
            message += "canceled."
        else:
            done = self.task.done()
            if done:
                message += "done."
            else:
                message += "running."
        try:
            self.task.exception()
        except asyncio.base_futures.InvalidStateError:
            message += "  No error has been encountered."
        else:
            message += "  An error has been encountered.  Please run `[p]cogupdater task error` and report it to Neuro Assassin on the help server."
        await ctx.send(message)

    @_group_update_task.command()
    async def error(self, ctx):
        """Gets the latest error of the update task."""
        try:
            e = self.task.exception()
        except asyncio.base_futures.InvalidStateError:
            message = "No error has been encountered."
        else:
            ex = traceback.format_exception(type(e), e, e.__traceback__)
            message = "An error has been encountered: ```py\n" + "".join(ex) + "```"
        await ctx.send(message)
