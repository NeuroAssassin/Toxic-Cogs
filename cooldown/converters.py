from redbot.core.commands import BadArgument, Converter
import argparse
from .utils import FullArgument

class NoExitParser(argparse.ArgumentParser):
	def error(self, message):
		raise BadArgument()

class Cargs(Converter):
	async def convert(self, ctx, argument):
		argument = argument.replace("—", "--")
		parser = NoExitParser(description="Cooldown Parser", add_help=False)
		parser.add_argument("--command", nargs="*", dest="command", default=[])
		parser.add_argument("--every", nargs="*", dest="every", default=[])
		parser.add_argument("--type", nargs="*", dest="type", default=[])
		try:
			vals = vars(parser.parse_args(argument.split(" ")))
		except Exception as exc:
			await ctx.send(exc)
			raise BadArgument() from exc
		vals['command'] = " ".join(vals['command'])
		vals['type'] = vals['type'][0]
		if (not vals['command']) or (not vals['every']) or (not vals['type']):
			await ctx.send("Not all arguments were filled.")
			raise BadArgument()
		if not ctx.bot.get_command(vals['command']):
			await ctx.send("Invalid command.")
			raise BadArgument()
		returning = FullArgument(vals['command'], ctx.bot.get_command(vals['command']), vals['type'], int(vals['every'][0]), vals['every'][1:])
		return returning