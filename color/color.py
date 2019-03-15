from redbot.core import commands
from colour import Color as col
from colour import rgb2hex
import discord

class Color(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    __author__ = "Neuro Assassin#4227 <@473541068378341376>"

    @commands.group(aliases=["colour"])
    async def color(self, ctx):
        """Group command for color commands"""
        pass

    @color.command()
    async def name(self, ctx, name):
        """Provides the hexadecimal value, RGB value and HSL value of a passed color.  For example, pass 'red' or 'blue' as the name argument."""
        name = name.lower()
        try:
            c = col(name)
            hexa = rgb2hex(c.rgb, force_long=True)
            embed = discord.Embed(title="Color Embed for: " + name, description="Hexadecimal, RGB and HSL values for: " + name, color=int(hexa.replace("#", "0x"), 0))
            embed.add_field(name="Hexadecimal Value:", value=hexa)
            embed.add_field(name="Red, Green, Blue (RGB) Value: ", value=str(c.rgb))
            embed.add_field(name="Hue, Saturation, Luminance (HSL) Value:", value=str(c.hsl))
            await ctx.send(embed=embed)
        except (ValueError, AttributeError):
            await ctx.send("That color is not recognized.")

    @color.command()
    async def hex(self, ctx, hexa: str):
        """Provides the RGB value and HSL value of a passed hexadecimal value.  Hexadecimal value must in the format of something like '#ffffff' or '0xffffff' to be used."""
        try:
            hexa = hexa.replace("0x", "#")
            c = col(hexa)
            embed = discord.Embed(title="Color Embed for: " + hexa, description="Hexadecimal and RGB values for: " + hexa, color=int(hexa.replace("#", "0x"), 0))
            embed.add_field(name="Hexadecimal Value:", value=hexa)
            embed.add_field(name="Red Green Blue (RGB) Value: ", value=str(c.rgb))
            embed.add_field(name="Hue, Saturation, Luminance (HSL) Value:", value=str(c.hsl))
            await ctx.send(embed=embed)
        except (ValueError, AttributeError):
            await ctx.send("That hexadecimal value is not recognized.")

    @color.command()
    async def rgb(self, ctx, highest: int, r: float, g: float, b: float):
        """Provides the hexadecimal value and HSL value of the rgb value given.  Each value must have a space between them.  Highest argument must be 1 or 255, indicating the highest value of a single value (r, g, or b)."""
        if not (highest in [1, 255]):
            return await ctx.send("Invalid `highest` argument.")
        if highest == 255:
            r = r / 255
            g = g / 255
            b = b / 255
        try:
            c = col(rgb=(r, g, b))
            values = (r*255, g*255, b*255)
            hexa = rgb2hex(c.rgb, force_long=True)
            embed = discord.Embed(title="Color Embed for: " + str(values), description="Hexadecimal and RGB values for: " + str(values), color=int(hexa.replace("#", "0x"), 0))
            embed.add_field(name="Hexadecimal Value:", value=hexa)
            embed.add_field(name="Red Green Blue (RGB) Value: ", value=str(c.rgb))
            embed.add_field(name="Hue, Saturation, Luminance (HSL) Value:", value=str(c.hsl))
            await ctx.send(embed=embed)
        except (ValueError, AttributeError):
            await ctx.send("That rgb number is not recognized.")

    @color.command()
    async def hsl(self, ctx, h: float, s: float, l: float):
        """Provides the hexadecimal value and the RGB value of the hsl value given.  Each value must have a space between them."""
        try:
            c = col(hsl=(h, s, l))
            values = (h, s, l)
            hexa = rgb2hex(c.rgb, force_long=True)
            embed = discord.Embed(title="Color Embed for: " + str(values), description="Hexadecimal and RGB values for: " + str(values), color=int(hexa.replace("#", "0x"), 0))
            embed.add_field(name="Hexadecimal Value:", value=hexa)
            embed.add_field(name="Red Green Blue: ", value=str(c.rgb))
            embed.add_field(name="Hue, Saturation, Luminance (HSL):", value=str(c.hsl))
            await ctx.send(embed=embed)
        except (ValueError, AttributeError):
            await ctx.send("That hsl number is not recognized.")