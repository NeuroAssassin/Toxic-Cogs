from redbot.core import commands
import aiohttp
from bs4 import BeautifulSoup

BaseCog = getattr(commands, "Cog", object)

class Webstatus(BaseCog):
    """Cog for seeing if something is down"""

    def __init__(self, bot):
        self.bot = bot

    async def fetch(self, session, url):
        async with session.get(url) as response:
            if response.status != 200:
                return int(await response.status)
            return await response.text()

    @commands.command()
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
                        await ctx.send(f"An error occurred within outage.report.  The site responded with status code {webpage}")
                        return
                soup = BeautifulSoup(webpage, 'html.parser')
                results = soup.find_all('div', attrs={'class': 'Alert__Div-s1eb33n4-0'})
                if len(results) == 0:
                    await ctx.send("https://outage.report has not reported any problems.")
                else:
                    await ctx.send(f"https://outage.report/ has reported: {results[0].string}")
                    reports = soup.find_all('text', attrs={'class': 'Gauge__Count-cx9u1z-5'})
                    await ctx.send(f"{reports[0].string} people have reported problems in the last 20 minutes.")
                    return