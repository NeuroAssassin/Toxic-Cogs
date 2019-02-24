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
        """Provides the hexadecimal value, RGB value and HSL value of a passed color.  For example, pass 'red' or 'blue'"""
        name = name.lower()
        try:
            c = col(name)
            hexa = rgb2hex(c.rgb, force_long=True).replace("#", "0x")
            embed = discord.Embed(title="Color Embed for: " + name, description="Hexadecimal and RGB values for: " + name, color=int(hexa, 0))
            embed.add_field(name="Hexadecimal Value:", value=hexa, inline=True)
            embed.add_field(name="Red Green Blue: ", value=str(c.rgb), inline=True)
            embed.add_field(name="Hue, Saturation, Luminance (HSL):", value=str(c.hsl), inline=True)
            await ctx.send(embed=embed)
            #await ctx.send("**Hexadecimal Value:** " + rgb2hex(c.rgb, force_long=True) + "\n**Red Green Blue:** " + str(c.rgb))
        except ValueError:
            await ctx.send("That color is not recognized.")
        except AttributeError:
            await ctx.send("That color is not recognized.")

    @color.command()
    async def hex(self, ctx, hexa: str):
        """Provides the RGB value and HSL value of a passed hexadecimal value.  Hexadecimal value must in the format of  something like '#ffffff' or '0xffffff'"""
        try:
            hexa = hexa.replace("0x", "#")
            c = col(hexa)
            hexa = hexa.replace("#", "0x")
            embed = discord.Embed(title="Color Embed for: " + hexa, description="Hexadecimal and RGB values for: " + hexa, color=int(hexa, 0))
            embed.add_field(name="Hexadecimal Value:", value=hexa, inline=True)
            embed.add_field(name="Red Green Blue: ", value=str(c.rgb), inline=True)
            embed.add_field(name="Hue, Saturation, Luminance (HSL):", value=str(c.hsl), inline=True)
            await ctx.send(embed=embed)
            #await ctx.send("**Hexadecimal Value: **" + hexa + "\n**Red Green Blue: **" + str(c.rgb))
        except ValueError:
            await ctx.send("That hexadecimal value is not recognized.")
        except AttributeError:
            await ctx.send("That hexadecimal value is not recognized.")

    @color.command()
    async def rgb(self, ctx, r: float, g: float, b: float):
        """Provides the hexadecimal value and HSL value of the rgb value given.  Each value must have a space between them."""
        if r+g+b > 3:
            r = r / 255
            g = g / 255
            b = b / 255
        try:
            c = col(rgb=(r, g, b))
            hexa = rgb2hex(c.rgb, force_long=True).replace("#", "0x")
            embed = discord.Embed(title="Color Embed for: " + str((r*255, g*255, b*255)), description="Hexadecimal and RGB values for: " + str((r*255, g*255, b*255)), color=int(hexa, 0))
            embed.add_field(name="Hexadecimal Value:", value=hexa, inline=True)
            embed.add_field(name="Red Green Blue: ", value=str(c.rgb), inline=True)
            embed.add_field(name="Hue, Saturation, Luminance (HSL):", value=str(c.hsl), inline=True)
            await ctx.send(embed=embed)
            #await ctx.send("**Hexadecimal Value: **" + rgb2hex(c.rgb, force_long=True) + "\n**Red Green Blue:** " + str((r, g, b)))
        except ValueError:
            await ctx.send("That rgb number is not recognized.")
        except AttributeError:
            await ctx.send("That rgb number is not recognized.")

    @color.command()
    async def hsl(self, ctx, h: float, s: float, l: float):
        """Provides the hexadecimal value and the RGB value of the hsl value given.  Each value must have a space between them."""
        try:
            c = col(hsl=(h, s, l))
            hexa = rgb2hex(c.rgb, force_long=True).replace("#", "0x")
            embed = discord.Embed(title="Color Embed for: " + str((h, s, l)), description="Hexadecimal and RGB values for: " + str((h, s, l)), color=int(hexa, 0))
            embed.add_field(name="Hexadecimal Value:", value=hexa, inline=True)
            embed.add_field(name="Red Green Blue: ", value=str(c.rgb), inline=True)
            embed.add_field(name="Hue, Saturation, Luminance (HSL):", value=str(c.hsl), inline=True)
            await ctx.send(embed=embed)
        except ValueError:
            await ctx.send("That hsl number is not recognized.")
        except AttributeError:
            await ctx.send("That hsl number is not recognized.")