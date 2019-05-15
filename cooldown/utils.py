from redbot.core.commands import BadArgument
import discord

def convert_time(value):
	if not value:
		return None
	value[1] = value[1].lower()
	passing = int(value[0])
	if value[1].startswith("second"):
		pass
	elif value[1].startswith("minute"):
		passing *= 60
	elif value[1].startswith("hour"):
		passing *= 3600
	elif value[1].startswith("day"):
		passing *= 86400
	else:
		raise BadArgument()
	return passing

class FullArgument:
	def __init__(self, name, command, btype, amount, every):
		self.name = " ".join(name)
		self.command = command
		switch = {
			"user": discord.ext.commands.BucketType.user,
			"channel": discord.ext.commands.BucketType.channel,
			"guild": discord.ext.commands.BucketType.guild,
			"global": discord.ext.commands.BucketType.default,
        }
		try:
			self.bucket = switch[btype]
		except KeyError:
			raise BadArgument()
		self.amount = amount
		self.every = convert_time(every)