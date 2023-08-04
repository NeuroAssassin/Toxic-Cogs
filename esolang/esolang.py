"""
MIT License

Copyright (c) 2018-Present NeuroAssassin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box
import traceback
import functools
import asyncio
import inspect

from .brainfuck import Brainfuck
from .cow import COW
from .befunge import Befunge
from .whitespace import Whitespace


class Esolang(commands.Cog):
    """Do not ever look at the source for this"""

    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner()
    @commands.command()
    async def brainfuck(self, ctx, *, code):
        """Run brainfuck code"""
        try:
            output, cells = Brainfuck.evaluate(code)
        except Exception as error:
            await ctx.send(
                box("".join(traceback.format_exception_only(type(error), error)), lang="py")
            )
        else:
            output.seek(0)
            output = output.read()
            await ctx.send(
                box(
                    f"[Memory]: {'[' + ']['.join(list(map(str, cells))) + ']'}\n"
                    f"[Output]: {output}",
                    lang="ini",
                )
            )

    @checks.is_owner()
    @commands.command()
    async def cow(self, ctx, *, code):
        """Run COW code"""
        try:
            output, cells = COW.evaluate(code)
        except Exception as error:
            await ctx.send(
                box("".join(traceback.format_exception_only(type(error), error)), lang="py")
            )
        else:
            output.seek(0)
            output = output.read()
            await ctx.send(
                box(
                    f"[Memory]: {'[' + ']['.join(list(map(str, cells))) + ']'}\n"
                    f"[Output]: {output}",
                    lang="ini",
                )
            )

    @checks.is_owner()
    @commands.command()
    async def befunge(self, ctx, *, code):
        """Run Befunge code"""
        if code.startswith("```") and code.endswith("```"):
            code = code[3:-3]

        try:
            task = self.bot.loop.create_task(Befunge.evaluate(code))
            await asyncio.wait_for(task, timeout=5.0)
            output, cells = task.result()
        except asyncio.TimeoutError:
            await ctx.send("Your befunge program took too long to run.")
        except Exception as error:
            frame_vars = inspect.trace()[-1][0].f_locals
            stack = frame_vars.get("stack", frame_vars.get("self"))
            if stack:
                stack = "[" + "][".join(list(map(str, stack._internal[:10]))) + "]"
            else:
                stack = "Not initialized"
            await ctx.send(
                box(
                    f"[Stack]: {stack}\n"
                    f"[Exception]:\n{''.join(traceback.format_exception_only(type(error), error))}",
                    lang="ini",
                )
            )
        else:
            output.seek(0)
            output = output.read()
            await ctx.send(
                box(
                    f"[Stack]: {'[' + ']['.join(list(map(str, cells))) + ']'}\n"
                    f"[Output]: {output}",
                    lang="ini",
                )
            )

    @checks.is_owner()
    @commands.command()
    async def whitespace(self, ctx, *, code):
        """Run whitepsace code.

        Since Discord auto-converts tabs to spaces, use EM QUAD instead.

        If you need to copy it, here: `\u2001`
        """
        try:
            wrapped = functools.partial(Whitespace.evaluate, code=code)
            future = self.bot.loop.run_in_executor(None, wrapped)
            for x in range(500):
                await asyncio.sleep(0.01)
                try:
                    output = future.result()
                except asyncio.InvalidStateError:
                    continue
                else:
                    break
        except Exception as error:
            await ctx.send(
                box("".join(traceback.format_exception_only(type(error), error)), lang="py")
            )
        else:
            output.seek(0)
            output = output.read()
            await ctx.send(
                box(
                    f"[Output]: {output}",
                    lang="ini",
                )
            )
