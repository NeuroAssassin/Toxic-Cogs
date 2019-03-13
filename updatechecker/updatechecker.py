# Huge thanks to Sinbad for allowing me to copy parts of his RSS cog, which I used to grab the latest commits from repositories.

# Also, the code I use for updating repos I took directly from Red, and just took out the message interactions

from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list, inline
import asyncio
import aiohttp
import feedparser
import discord
import traceback
from typing import Optional

class UpdateChecker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.conf = Config.get_conf(self, identifier=473541068378341376)
        default_global = {"updated": False, "repos": {}, "auto": False}
        self.conf.register_global(**default_global)
        self.task = self.bot.loop.create_task(self.bg_task())

    def __unload(self):
        self.task.cancel()
        self.session.detach()

    async def bg_task(self):
        await self.bot.wait_until_ready()
        # To make owner gets set
        await asyncio.sleep(10)
        while True:
            updated = await self.conf.updated()
            if updated:
                cog = self.bot.get_cog("Downloader")
                if cog != None:
                    repos = await self.conf.repos()
                    auto  = await self.conf.auto()
                    owner = self.bot.get_user(self.bot.owner_id)
                    for repo_name, commit_saved in repos.items():
                        repo = cog._repo_manager.get_repo(repo_name)
                        url = repo.url + r"/commits/" + repo.branch + ".atom"
                        response = await self.fetch_feed(url)
                        commit = response.entries[0]['title']
                        if commit != commit_saved:
                            if not auto:
                                try:
                                    await owner.send(f"[Update Checker]: Update available for repo: {repo.name}")
                                except discord.errors.Forbidden:
                                    pass
                            else:
                                try:
                                    await owner.send(f"[Update Checker] Update found for repo: {repo.name}.  Updating repos...")
                                except discord.errors.Forbidden:
                                    pass
                                # Just a copy of `[p]cog update`, but without using ctx things
                                try:
                                    installed_cogs = set(await cog.installed_cogs())
                                    updated = await cog._repo_manager.update_all_repos()
                                    updated_cogs = set(cog for repo in updated for cog in repo.available_cogs)
                                    installed_and_updated = updated_cogs & installed_cogs
                                    if installed_and_updated:
                                        await cog._reinstall_requirements(installed_and_updated)
                                        await cog._reinstall_cogs(installed_and_updated)
                                        await cog._reinstall_libraries(installed_and_updated)
                                        cognames = {c.name for c in installed_and_updated}
                                        message = humanize_list(tuple(map(inline, cognames)))
                                except Exception as error:
                                    exception_log = "Exception while updating repos in Update Checker \n"
                                    exception_log += "".join(
                                        traceback.format_exception(type(error), error, error.__traceback__)
                                    )
                                    try:
                                        await owner.send(f"[Update Checker]: Error while updating repos.\n\n{exception_log}")
                                    except discord.errors.Forbidden:
                                        pass
                                else:
                                    try:
                                        await owner.send(f"[Update Checker]: Ran cog update.  Updated cogs: {message}")
                                    except discord.errors.Forbidden:
                                        pass
                            repos[repo.name] = commit
                            await self.conf.repos.set(repos)
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

    @commands.group()
    async def update(self, ctx):
        """Group command for controlling the update checker cog"""
        pass

    @update.command(name="all")
    async def _update_all(self, ctx):
        """Runs `[p]cog update`, then saves all of the commits"""
        await self.conf.updated.set(True)
        cog = self.bot.get_cog("Downloader")
        await ctx.invoke(cog._cog_update)
        await ctx.send("Done invoking cog update command.  Getting latest commits and storing them...")
        repos = cog._repo_manager.get_all_repo_names()
        real_repos = []
        for repo_name in repos:
            repo = cog._repo_manager.get_repo(repo_name)
            real_repos.append(repo)
        data = await self.conf.repos()
        for repo in real_repos:
            url = repo.url + r"/commits/" + repo.branch + ".atom"
            response = await self.fetch_feed(url)
            commit = response.entries[0]['title']
            data[repo.name] = commit
        await self.conf.repos.set(data)
        await ctx.send("The latest commits for all of your repos have been saved.  You will be notified when an update is available.")

    @update.command()
    async def auto(self, ctx):
        """Changes automatic cog updates to the opposite setting."""
        auto = await self.conf.auto()
        await self.conf.auto.set(not auto)
        status = "disabled" if auto else "enabled"
        await ctx.send(f"Auto cog updates are now {status}")