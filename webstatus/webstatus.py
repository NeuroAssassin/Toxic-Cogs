from redbot.core import commands
import aiohttp
from bs4 import BeautifulSoup
import discord

BaseCog = getattr(commands, "Cog", object)

class Webstatus(BaseCog):
    """Cog for seeing if something is down"""

    def __init__(self, bot):
        self.bot = bot

    async def fetch(self, session, url):
        async with session.get(url) as response:
            if response.status != 200:
                return int(response.status)
            return await response.text()

    @commands.command(hidden=True)
    async def webstatus(self, ctx, *, company):
        """Uses https://outage.report/ to see if the company/website is down"""
        # Filter out https's and www's
        if company.startswith("https://www."):
            company = company[12:]
        elif company.startswith("http://www."):
            company = company[11:]
        elif company.startswith("https://") and company[8:12] != "www.":
            company = company[8:]
        elif company.startswith("http://") and company[7:11] != "www.":
            company = company[7:]
        elif company.startswith("www."):
            company = company[4:]

        # Filter out suffixes
        if company.endswith(".com"):
            company = company[:(len(company)-4)]
        elif company.endswith(".org"):
            company = company[:(len(company)-4)]
        elif company.endswith(".net"):
            company = company[:(len(company)-4)]
        elif company.endswith(".gov"):
            company = company[:(len(company)-4)]
        elif company.endswith(".edu"):
            company = company[:(len(company)-4)]
        async with aiohttp.ClientSession() as session:
            try:
                url = "https://outage.report/" + company.replace(' ', '').lower()
                webpage = await self.fetch(session, url)
            except Exception as e:
                await ctx.send(f"An error occurred while fetching the status.")
                print(e)
                return
            else:
                if type(webpage) == int:
                    if webpage != 200:
                        if webpage == 404:
                            await ctx.send("It looks like either one of the following scenarios has happened:\n**1.** outage.report doesn't follow that site\n**2.** This cog didn't parse your input well\n**3.** You entered an incorrect site.")
                        else:
                            await ctx.send(f"An error occurred within outage.report.  The site responded with status code {webpage}")
                        return
                soup = BeautifulSoup(webpage, 'html.parser')
                results = soup.find_all('div', attrs={'class': 'Alert__Div-s1eb33n4-0'})
                if len(results) == 0:
                    embed = discord.Embed(title="Results", description="Results from outage.report", color=0x00ff00)
                    embed.add_field(name="Status:", value="No reported problems on outage.report", inline=True)
                    await ctx.send(embed=embed)
                else:
                    embed = discord.Embed(title="Results", description="Results from outage.report", color=0xff0000)
                    embed.add_field(name="Status:", value=results[0].string, inline=True)
                    #await ctx.send(f"https://outage.report/ has reported: {results[0].string}")
                    reports = soup.find_all('text', attrs={'class': 'Gauge__Count-cx9u1z-5'})
                    embed.add_field(name="Reports:", value=f"Within the last 20 minutes, {reports[0].string} people reported problems")
                    await ctx.send(embed=embed)