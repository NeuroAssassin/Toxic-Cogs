from redbot.core import commands, Config, checks
from PIL import Image
from colour import Color as col
from colour import rgb2hex
import discord
import io
import re
import functools


class Color(commands.Cog):
    """View embeds showcasing the supplied color and information about it"""

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=473541068378341376)

        self.conf.register_guild(enabled=False)

        self.r = re.compile(
            r"(?i)^(?:(?:(?:0x|#|)((?:[a-fA-F0-9]{3}){1,2}$))|(?:([+-]?(?:[0-9]*[.])?[0-9]+,[+-]?(?:[0-9]*[.])?[0-9]+,[+-]?(?:[0-9]*[.])?[0-9]+))|(?:(\S+)))"
        )  # The Regex gods are going to kill me

    __author__ = "Neuro Assassin#4779 <@473541068378341376>"

    def have_fun_with_pillow(self, rgb):
        im = Image.new("RGB", (200, 200), rgb)
        f = io.BytesIO()
        im.save(f, format="png")
        f.seek(0)
        file = discord.File(f, filename="picture.png")
        return file

    async def build_embed(self, co):
        rgb = [int(c * 255) for c in co.rgb]
        rgb = tuple(rgb)
        file = await self.bot.loop.run_in_executor(None, self.have_fun_with_pillow, rgb)
        hexa = rgb2hex(co.rgb, force_long=True)
        embed = discord.Embed(
            title=f"Color Embed for: {hexa}", color=int(hexa.replace("#", "0x"), 0)
        )
        embed.add_field(name="Hexadecimal Value:", value=hexa)
        normal = ", ".join([f"{part:.2f}" for part in co.rgb])
        extended = ", ".join([f"{(part*255):.2f}" for part in co.rgb])
        embed.add_field(name="Red, Green, Blue (RGB) Value: ", value=f"{normal}\n{extended}")
        embed.add_field(name="Hue, Saturation, Luminance (HSL) Value:", value=str(co.hsl))
        embed.set_thumbnail(url="attachment://picture.png")
        return embed, file

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild and not (await self.conf.guild(message.guild).enabled()):
            return
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return
        words = message.content.split(" ")
        counter = 0
        for word in words:
            if counter == 3:
                return
            if word.startswith("#"):
                word = word[1:]
                m = self.r.match(word)
                if not m:
                    continue
                if m.group(1):  # Hex
                    hexa = m.group(1)
                    try:
                        c = col(f"#{hexa}")
                        embed, file = await self.build_embed(c)
                        await message.channel.send(file=file, embed=embed)
                        counter += 1
                    except (ValueError, AttributeError):
                        pass
                elif m.group(2):  # RGB
                    try:
                        stuff = m.group(2)
                        tup = tuple(stuff.split(","))
                        if any([float(item) > 1 for item in tup]):
                            tup = tuple([float(item) / 255 for item in tup])
                        tup = tuple(map(float, tup))
                        try:
                            c = col(rgb=tup)
                            embed, file = await self.build_embed(c)
                            await message.channel.send(file=file, embed=embed)
                            counter += 1
                        except (ValueError, AttributeError) as e:
                            await message.channel.send(f"Not recognized: {tup}; {e}")
                    except Exception as e:
                        await message.channel.send(e)
                elif m.group(3):  # Named
                    name = m.group(3)
                    try:
                        c = col(name)
                        embed, file = await self.build_embed(c)
                        await message.channel.send(file=file, embed=embed)
                        counter += 1
                    except (ValueError, AttributeError):
                        pass

    @commands.group(aliases=["colour"])
    async def color(self, ctx):
        """Group command for color commands"""
        pass

    @checks.bot_has_permissions(embed_links=True)
    @color.command()
    async def name(self, ctx, name):
        """Provides the hexadecimal value, RGB value and HSL value of a passed color.  For example, pass `red` or `blue` as the name argument."""
        name = name.lower()
        try:
            c = col(name)
            embed, file = await self.build_embed(c)
            await ctx.send(file=file, embed=embed)
        except (ValueError, AttributeError):
            await ctx.send("That color is not recognized.")

    @checks.bot_has_permissions(embed_links=True)
    @color.command()
    async def hex(self, ctx, hexa: str):
        """Provides the RGB value and HSL value of a passed hexadecimal value.  Hexadecimal value must in the format of something like `#ffffff` or `0xffffff` to be used."""
        try:
            match = re.match(r"(?i)^(?:0x|#|)((?:[a-fA-F0-9]{3}){1,2})$", hexa)
            c = col("#" + match.group(1))
            embed, file = await self.build_embed(c)
            await ctx.send(file=file, embed=embed)
        except (ValueError, AttributeError):
            await ctx.send("That hexadecimal value is not recognized.")
        except IndexError:
            await ctx.send(
                "Invalid formatting for the hexadecimal.  Must be the hexadecimal value, with an optional `0x` or `#` in the beginning."
            )

    @checks.bot_has_permissions(embed_links=True)
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
            embed, file = await self.build_embed(c)
            await ctx.send(file=file, embed=embed)
        except (ValueError, AttributeError):
            await ctx.send("That rgb number is not recognized.")

    @checks.bot_has_permissions(embed_links=True)
    @color.command()
    async def hsl(self, ctx, h: float, s: float, l: float):
        """Provides the hexadecimal value and the RGB value of the hsl value given.  Each value must have a space between them."""
        try:
            c = col(hsl=(h, s, l))
            embed, file = await self.build_embed(c)
            await ctx.send(file=file, embed=embed)
        except (ValueError, AttributeError):
            await ctx.send("That hsl number is not recognized.")

    @checks.admin()
    @color.command()
    async def msgshort(self, ctx, enable: bool):
        """Enable or disable the in-message shortcut.
        
        In-message shortcuts can be used by using the hex, rgb or name after a `#` in the middle of a message, as follows:
        
        `#000000` (hex)
        `#1,1,1` (rgb)
        `#black` (named)"""
        await self.conf.guild(ctx.guild).enabled.set(enable)
        if enable:
            await ctx.send("The in-message shortcut is now enabled.")
        else:
            await ctx.send("The in-message shortcut is now disabled.")
