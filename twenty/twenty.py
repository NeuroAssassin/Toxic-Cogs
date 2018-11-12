import random
from redbot.core import commands, checks
import asyncio

BaseCog = getattr(commands, "Cog", object)

class Twenty(BaseCog):
	"""Cog for playing 2048 inside of Discord!"""
	def __init__(self, bot):
		self.board = [
			["_", "_", "_", "_"],
			["_", "_", "_", "_"],
			["_", "_", "_", "_"],
			["_", "_", "_", 2]
		]
		self.bot = bot
		self.game_active = False

	@commands.group()
	async def twenty(self, ctx):
		"""Group command for starting a 2048 game"""
		pass

	@twenty.command()
	async def start(self, ctx):
		"""Starts a 2048 game inside of Discord"""
		if self.game_active == True:
			await ctx.send("A game is already in use.  Please try again later.")
			return
		else:
			self.game_active = True
		start = await ctx.send("Starting game...")
		await ctx.send("If a reaction is not received every 5 minutes, the game will time out.")
		message = await ctx.send("```" + self.print_board() + "```")
		await message.add_reaction("\u2B06")
		await message.add_reaction("\u2B07")
		await message.add_reaction("\u2B05")
		await message.add_reaction("\u27A1")
		await message.add_reaction("\u274C")

		def check(reaction, user):
			return (user == ctx.author) and str(reaction.emoji) in ["\u2B06", "\u2B07", "\u2B05", "\u27A1", "\u274C"]
		while True:
			try:
				reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=300.0)
			except asyncio.TimeoutError:
				await ctx.send("Ending game")
				self.board = [
					["_", "_", "_", "_"],
					["_", "_", "_", "_"],
					["_", "_", "_", "_"],
					["_", "_", "_", 2]
				]
				await message.delete()
				self.game_active = False
				return
			else:
				if str(reaction.emoji) == "\u2B06":
					await message.remove_reaction("\u2B06", ctx.author)
					msg = self.execute_move("up")
				elif str(reaction.emoji) == "\u2B07":
					await message.remove_reaction("\u2B07", ctx.author)
					msg = self.execute_move("down")
				elif str(reaction.emoji) == "\u2B05":
					await message.remove_reaction("\u2B05", ctx.author)
					msg = self.execute_move("left")
				elif str(reaction.emoji) == "\u27A1":
					await message.remove_reaction("\u27A1", ctx.author)
					msg = self.execute_move('right')
				elif str(reaction.emoji) == "\u274C":
					await ctx.send("Ending game")
					await message.delete()
					self.board = [
						["_", "_", "_", "_"],
						["_", "_", "_", "_"],
						["_", "_", "_", "_"],
						["_", "_", "_", 2]
					]
					self.game_active = False
					return
				if msg == "Lost":
					await ctx.send(f"On no!  It appears you have lost {ctx.author.mention}")
					await asyncio.sleep(5)
					await message.delete()
					self.board = [
						["_", "_", "_", "_"],
						["_", "_", "_", "_"],
						["_", "_", "_", "_"],
						["_", "_", "_", 2]
					]
					self.game_active = False
					return
				await message.edit(content = "```" + self.print_board() + "```")
		
	def print_board(self):
		col_width = max(len(str(word)) for row in self.board for word in row) + 2  # padding
		whole_thing = ""
		for row in self.board:
			whole_thing += "".join(str(word).ljust(col_width) for word in row) + '\n'
		return whole_thing
	def execute_move(self, move):
		if move.lower() == "left":
			self.check_left()
			for x in range(len(self.board)):
				while self.board[x][0] == '_' and (self.board[x][1] != '_' or self.board[x][2] != '_' or self.board[x][3] != '_'):
					self.board[x][0] = self.board[x][1]
					self.board[x][1] = self.board[x][2]
					self.board[x][2] = self.board[x][3]
					self.board[x][3] = '_'
				while self.board[x][1] == '_' and (self.board[x][2] != '_' or self.board[x][3] != '_'):
					self.board[x][1] = self.board[x][2]
					self.board[x][2] = self.board[x][3]
					self.board[x][3] = '_'
				while self.board[x][2] == '_' and (self.board[x][3] != '_'):
					self.board[x][2] = self.board[x][3]
					self.board[x][3] = '_'
		if move.lower() == 'right':
			self.check_right()
			for x in range(len(self.board)):
				while self.board[x][3] == '_' and (self.board[x][2] != '_' or self.board[x][1] != '_' or self.board[x][0] != '_'):
					self.board[x][3] = self.board[x][2]
					self.board[x][2] = self.board[x][1]
					self.board[x][1] = self.board[x][0]
					self.board[x][0] = '_'
				while self.board[x][2] == '_' and (self.board[x][1] != '_' or self.board[x][0] != '_'):
					self.board[x][2] = self.board[x][1]
					self.board[x][1] = self.board[x][0]
					self.board[x][0] = '_'
				while self.board[x][1] == '_' and (self.board[x][0] != '_'):
					self.board[x][1] = self.board[x][0]
					self.board[x][0] = '_'
		if move.lower() == 'down':
			self.columize()
			self.check_down()
			for x in range(len(self.board)):
				while self.board[x][0] == '_' and (self.board[x][1] != '_' or self.board[x][2] != '_' or self.board[x][3] != '_'):
					self.board[x][0] = self.board[x][1]
					self.board[x][1] = self.board[x][2]
					self.board[x][2] = self.board[x][3]
					self.board[x][3] = '_'
				while self.board[x][1] == '_' and (self.board[x][2] != '_' or self.board[x][3] != '_'):
					self.board[x][1] = self.board[x][2]
					self.board[x][2] = self.board[x][3]
					self.board[x][3] = '_'
				while self.board[x][2] == '_' and (self.board[x][3] != '_'):
					self.board[x][2] = self.board[x][3]
					self.board[x][3] = '_'
			self.rowize()
		if move.lower() == 'up':
			self.columize()
			self.check_up()
			for x in range(len(self.board)):
				while self.board[x][3] == '_' and (self.board[x][2] != '_' or self.board[x][1] != '_' or self.board[x][0] != '_'):
					self.board[x][3] = self.board[x][2]
					self.board[x][2] = self.board[x][1]
					self.board[x][1] = self.board[x][0]
					self.board[x][0] = '_'
				while self.board[x][2] == '_' and (self.board[x][1] != '_' or self.board[x][0] != '_'):
					self.board[x][2] = self.board[x][1]
					self.board[x][1] = self.board[x][0]
					self.board[x][0] = '_'
				while self.board[x][1] == '_' and (self.board[x][0] != '_'):
					self.board[x][1] = self.board[x][0]
					self.board[x][0] = '_'
			self.rowize()
		some_message = self.add_number()
		if some_message.startswith("Lost"):
			return "Lost"
		else:
			return ""

	def add_number(self):
		try:
			row = random.randint(0, 3)
		except RecursionError:
			return "Lost"
		if "_" in self.board[row]:
			number_of_zeroes = self.board[row].count("_")
			if number_of_zeroes == 1:
				column = self.board[row].index("_")
			else:
				column = random.randint(0, 3)
				while self.board[row][column] != '_':
					column = random.randint(0, 3)
		else:
			self.add_number()
			return ""
		joining = random.randint(0, 100)
		if joining < 75:
			joining = 2
		else:
			joining = 4
		self.board[row][column] = joining
		return ""
		
	def columize(self):
		new_board = [
			[],
			[],
			[],
			[]
		]
		#Make first column
		new_board[0].append(self.board[3][0])
		new_board[0].append(self.board[2][0])
		new_board[0].append(self.board[1][0])
		new_board[0].append(self.board[0][0])
		#Make second column
		new_board[1].append(self.board[3][1])
		new_board[1].append(self.board[2][1])
		new_board[1].append(self.board[1][1])
		new_board[1].append(self.board[0][1])
		#Make third column
		new_board[2].append(self.board[3][2])
		new_board[2].append(self.board[2][2])
		new_board[2].append(self.board[1][2])
		new_board[2].append(self.board[0][2])
		#Make fourth column
		new_board[3].append(self.board[3][3])
		new_board[3].append(self.board[2][3])
		new_board[3].append(self.board[1][3])
		new_board[3].append(self.board[0][3])
		#Columns are saved as the new_board[0] is the left-most column, and new_board[0][0] is the bottom-right hand corner number
		self.board = new_board
	def rowize(self):
		new_board = [
			[],
			[],
			[],
			[]
		]
		#Make first row
		new_board[0].append(self.board[0][3])
		new_board[0].append(self.board[1][3])
		new_board[0].append(self.board[2][3])
		new_board[0].append(self.board[3][3])
		#Make second row
		new_board[1].append(self.board[0][2])
		new_board[1].append(self.board[1][2])
		new_board[1].append(self.board[2][2])
		new_board[1].append(self.board[3][2])
		#Make third row
		new_board[2].append(self.board[0][1])
		new_board[2].append(self.board[1][1])
		new_board[2].append(self.board[2][1])
		new_board[2].append(self.board[3][1])
		#Make fourth row
		new_board[3].append(self.board[0][0])
		new_board[3].append(self.board[1][0])
		new_board[3].append(self.board[2][0])
		new_board[3].append(self.board[3][0])
		self.board = new_board

	def check_left(self):
		for x in range(len(self.board)):
			for y in range(len(self.board[x])):
				try:
					if self.board[x][y+1] != '_':
						if self.board[x][y] == self.board[x][y+1]:
							self.board[x][y] = self.board[x][y] + self.board[x][y+1]
							self.board[x][y+1] = '_'
					elif self.board[x][y+2] != '_':
						if self.board[x][y] == self.board[x][y+2]:
							self.board[x][y] = self.board[x][y] + self.board[x][y+2]
							self.board[x][y+2] = '_'
					elif self.board[x][y+3] != '_':
						if self.board[x][y] == self.board[x][y+3]:
							self.board[x][y] = self.board[x][y] + self.board[x][y+3]
							self.board[x][y+3] = '_'
				except IndexError as e:
					pass

	def check_right(self):
		for x in range(len(self.board)):
			for y in range(len(self.board[x])):
				try:
					if self.board[x][y-1] != '_' and y - 1 >= 0:
						if self.board[x][y] == self.board[x][y-1]:
							self.board[x][y] = self.board[x][y] + self.board[x][y-1]
							self.board[x][y-1] = '_'
					elif self.board[x][y-2] != '_' and y - 2 >= 0:
						if self.board[x][y] == self.board[x][y-2]:
							self.board[x][y] = self.board[x][y] + self.board[x][y-2]
							self.board[x][y-2] = '_'
					elif self.board[x][y-3] != '_' and y - 3 >= 0:
						if self.board[x][y] == self.board[x][y-3]:
							self.board[x][y] = self.board[x][y] + self.board[x][y-3]
							self.board[x][y-3] = '_'
				except IndexError as e:
					pass

	def check_up(self):
		for x in range(len(self.board)):
			for y in range(len(self.board[x])):
				try:
					if self.board[x][y-1] != '_' and y - 1 >= 0:
						if self.board[x][y] == self.board[x][y-1]:
							self.board[x][y] = self.board[x][y] + self.board[x][y-1]
							self.board[x][y-1] = '_'
					elif self.board[x][y-2] != '_' and y - 2 >= 0:
						if self.board[x][y] == self.board[x][y-2]:
							self.board[x][y] = self.board[x][y] + self.board[x][y-2]
							self.board[x][y-2] = '_'
					elif self.board[x][y-3] != '_' and y - 3 >= 0:
						if self.board[x][y] == self.board[x][y-3]:
							self.board[x][y] = self.board[x][y] + self.board[x][y-3]
							self.board[x][y-3] = '_'
				except IndexError as e:
					pass
	def check_down(self):
		for x in range(len(self.board)):
			for y in range(len(self.board[x])):
				try:
					if self.board[x][y+1] != '_':
						if self.board[x][y] == self.board[x][y+1]:
							self.board[x][y] = self.board[x][y] + self.board[x][y+1]
							self.board[x][y+1] = '_'
					elif self.board[x][y+2] != '_':
						if self.board[x][y] == self.board[x][y+2]:
							self.board[x][y] = self.board[x][y] + self.board[x][y+2]
							self.board[x][y+2] = '_'
					elif self.board[x][y+3] != '_':
						if self.board[x][y] == self.board[x][y+3]:
							self.board[x][y] = self.board[x][y] + self.board[x][y+3]
							self.board[x][y+3] = '_'
				except IndexError as e:
					pass
