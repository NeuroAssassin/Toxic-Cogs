from redbot.core import commands, checks
import discord
import asyncio
import random
from copy import deepcopy as dc


class Twenty(commands.Cog):
    """Cog for playing 2048 inside of Discord!"""

    def __init__(self, bot):
        self.bot = bot

    __author__ = "Neuro Assassin#4779 <@473541068378341376>"

    @checks.bot_has_permissions(add_reactions=True)
    @commands.command()
    async def twenty(self, ctx):
        """Starts a 2048 game inside of Discord."""
        board = [
            ["_", "_", "_", "_"],
            ["_", "_", "_", "_"],
            ["_", "_", "_", "_"],
            ["_", "_", "_", 2],
        ]
        score = 0
        total = 0
        await ctx.send(
            "Starting game...\nIf a reaction is not received every 5 minutes, the game will time out."
        )
        message = await ctx.send(f"Score: **{score}**```{self.print_board(board)}```")
        await message.add_reaction("\u2B06")
        await message.add_reaction("\u2B07")
        await message.add_reaction("\u2B05")
        await message.add_reaction("\u27A1")
        await message.add_reaction("\u274C")

        def check(reaction, user):
            return (
                (user.id == ctx.author.id)
                and (str(reaction.emoji) in ["\u2B06", "\u2B07", "\u2B05", "\u27A1", "\u274C"])
                and (reaction.message.id == message.id)
            )

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=check, timeout=300.0
                )
            except asyncio.TimeoutError:
                await ctx.send("Ending game")
                await message.delete()
                return
            else:
                try:
                    await message.remove_reaction(str(reaction.emoji), ctx.author)
                except discord.errors.Forbidden:
                    pass
                if str(reaction.emoji) == "\u2B06":
                    msg, nb, total = self.execute_move("up", board)
                elif str(reaction.emoji) == "\u2B07":
                    msg, nb, total = self.execute_move("down", board)
                elif str(reaction.emoji) == "\u2B05":
                    msg, nb, total = self.execute_move("left", board)
                elif str(reaction.emoji) == "\u27A1":
                    msg, nb, total = self.execute_move("right", board)
                elif str(reaction.emoji) == "\u274C":
                    await ctx.send("Ending game")
                    await message.delete()
                    return
                score += total
                if msg == "Lost":
                    await ctx.send(
                        f"Oh no!  It appears you have lost {ctx.author.mention}.  You finished with a score of {score}!"
                    )
                    await message.delete()
                    return
                board = nb
                await message.edit(content=f"Score: **{score}**```{self.print_board(board)}```")

    def print_board(self, board):
        col_width = max(len(str(word)) for row in board for word in row) + 2  # padding
        whole_thing = ""
        for row in board:
            whole_thing += "".join(str(word).ljust(col_width) for word in row) + "\n"
        return whole_thing

    def execute_move(self, move, pboard):
        board = dc(pboard)
        total = 0
        if move.lower() == "left":
            nb, total = self.check_left(board)
            for x in range(len(nb)):
                while nb[x][0] == "_" and (nb[x][1] != "_" or nb[x][2] != "_" or nb[x][3] != "_"):
                    nb[x][0] = nb[x][1]
                    nb[x][1] = nb[x][2]
                    nb[x][2] = nb[x][3]
                    nb[x][3] = "_"
                while nb[x][1] == "_" and (nb[x][2] != "_" or nb[x][3] != "_"):
                    nb[x][1] = nb[x][2]
                    nb[x][2] = nb[x][3]
                    nb[x][3] = "_"
                while nb[x][2] == "_" and (nb[x][3] != "_"):
                    nb[x][2] = nb[x][3]
                    nb[x][3] = "_"
        if move.lower() == "right":
            nb, total = self.check_right(board)
            for x in range(len(nb)):
                while nb[x][3] == "_" and (nb[x][2] != "_" or nb[x][1] != "_" or nb[x][0] != "_"):
                    nb[x][3] = nb[x][2]
                    nb[x][2] = nb[x][1]
                    nb[x][1] = nb[x][0]
                    nb[x][0] = "_"
                while nb[x][2] == "_" and (nb[x][1] != "_" or nb[x][0] != "_"):
                    nb[x][2] = nb[x][1]
                    nb[x][1] = nb[x][0]
                    nb[x][0] = "_"
                while nb[x][1] == "_" and (nb[x][0] != "_"):
                    nb[x][1] = nb[x][0]
                    nb[x][0] = "_"
        if move.lower() == "down":
            nb = self.columize(board)
            nb, total = self.check_down(nb)
            for x in range(len(nb)):
                while nb[x][0] == "_" and (nb[x][1] != "_" or nb[x][2] != "_" or nb[x][3] != "_"):
                    nb[x][0] = nb[x][1]
                    nb[x][1] = nb[x][2]
                    nb[x][2] = nb[x][3]
                    nb[x][3] = "_"
                while nb[x][1] == "_" and (nb[x][2] != "_" or nb[x][3] != "_"):
                    nb[x][1] = nb[x][2]
                    nb[x][2] = nb[x][3]
                    nb[x][3] = "_"
                while nb[x][2] == "_" and (nb[x][3] != "_"):
                    nb[x][2] = nb[x][3]
                    nb[x][3] = "_"
            nb = self.rowize(nb)
        if move.lower() == "up":
            nb = self.columize(board)
            nb, total = self.check_up(nb)
            for x in range(len(nb)):
                while nb[x][3] == "_" and (nb[x][2] != "_" or nb[x][1] != "_" or nb[x][0] != "_"):
                    nb[x][3] = nb[x][2]
                    nb[x][2] = nb[x][1]
                    nb[x][1] = nb[x][0]
                    nb[x][0] = "_"
                while nb[x][2] == "_" and (nb[x][1] != "_" or nb[x][0] != "_"):
                    nb[x][2] = nb[x][1]
                    nb[x][1] = nb[x][0]
                    nb[x][0] = "_"
                while nb[x][1] == "_" and (nb[x][0] != "_"):
                    nb[x][1] = nb[x][0]
                    nb[x][0] = "_"
            nb = self.rowize(nb)
        if (
            nb != pboard
        ):  # So the user doesn't make a move that doesn't change anything, and just add a number
            some_message, nb = self.add_number(nb)
        else:
            some_message = ""
        if some_message.startswith("Lost"):
            return "Lost", nb, total
        else:
            return "", nb, total

    def add_number(self, board):
        try:
            row = random.randint(0, 3)
        except RecursionError:
            return "Lost", board
        if "_" in board[row]:
            number_of_zeroes = board[row].count("_")
            if number_of_zeroes == 1:
                column = board[row].index("_")
            else:
                column = random.randint(0, 3)
                while board[row][column] != "_":
                    column = random.randint(0, 3)
        else:
            result, board = self.add_number(board)
            return result, board
        joining = random.randint(0, 100)
        if joining < 85:
            joining = 2
        else:
            joining = 4
        board[row][column] = joining
        return "", board

    def columize(self, board):
        new_board = [[], [], [], []]
        # Make first column
        new_board[0].append(board[3][0])
        new_board[0].append(board[2][0])
        new_board[0].append(board[1][0])
        new_board[0].append(board[0][0])
        # Make second column
        new_board[1].append(board[3][1])
        new_board[1].append(board[2][1])
        new_board[1].append(board[1][1])
        new_board[1].append(board[0][1])
        # Make third column
        new_board[2].append(board[3][2])
        new_board[2].append(board[2][2])
        new_board[2].append(board[1][2])
        new_board[2].append(board[0][2])
        # Make fourth column
        new_board[3].append(board[3][3])
        new_board[3].append(board[2][3])
        new_board[3].append(board[1][3])
        new_board[3].append(board[0][3])
        board = new_board
        return board

    def rowize(self, board):
        new_board = [[], [], [], []]
        # Make first row
        new_board[0].append(board[0][3])
        new_board[0].append(board[1][3])
        new_board[0].append(board[2][3])
        new_board[0].append(board[3][3])
        # Make second row
        new_board[1].append(board[0][2])
        new_board[1].append(board[1][2])
        new_board[1].append(board[2][2])
        new_board[1].append(board[3][2])
        # Make third row
        new_board[2].append(board[0][1])
        new_board[2].append(board[1][1])
        new_board[2].append(board[2][1])
        new_board[2].append(board[3][1])
        # Make fourth row
        new_board[3].append(board[0][0])
        new_board[3].append(board[1][0])
        new_board[3].append(board[2][0])
        new_board[3].append(board[3][0])
        board = new_board
        return board

    def check_left(self, board):
        total = 0
        for x in range(len(board)):
            for y in range(len(board[x])):
                try:
                    if board[x][y + 1] != "_":
                        if board[x][y] == board[x][y + 1]:
                            board[x][y] = board[x][y] + board[x][y + 1]
                            total += board[x][y]
                            board[x][y + 1] = "_"
                    elif board[x][y + 2] != "_":
                        if board[x][y] == board[x][y + 2]:
                            board[x][y] = board[x][y] + board[x][y + 2]
                            total += board[x][y]
                            board[x][y + 2] = "_"
                    elif board[x][y + 3] != "_":
                        if board[x][y] == board[x][y + 3]:
                            board[x][y] = board[x][y] + board[x][y + 3]
                            total += board[x][y]
                            board[x][y + 3] = "_"
                except IndexError:
                    pass
        return board, total

    def check_right(self, board):
        total = 0
        for x in range(len(board)):
            board[x].reverse()
            for y in range(len(board[x])):
                try:
                    if board[x][y + 1] != "_":
                        if board[x][y] == board[x][y + 1]:
                            board[x][y] = board[x][y] + board[x][y + 1]
                            total += board[x][y]
                            board[x][y + 1] = "_"
                    elif board[x][y + 2] != "_":
                        if board[x][y] == board[x][y + 2]:
                            board[x][y] = board[x][y] + board[x][y + 2]
                            total += board[x][y]
                            board[x][y + 2] = "_"
                    elif board[x][y + 3] != "_":
                        if board[x][y] == board[x][y + 3]:
                            board[x][y] = board[x][y] + board[x][y + 3]
                            total += board[x][y]
                            board[x][y + 3] = "_"
                except IndexError:
                    pass
            board[x].reverse()
        return board, total

    def check_up(self, board):
        total = 0
        for x in range(len(board)):
            board[x].reverse()
            for y in range(len(board[x])):
                try:
                    if board[x][y + 1] != "_":
                        if board[x][y] == board[x][y + 1]:
                            board[x][y] = board[x][y] + board[x][y + 1]
                            total += board[x][y]
                            board[x][y + 1] = "_"
                    elif board[x][y + 2] != "_":
                        if board[x][y] == board[x][y + 2]:
                            board[x][y] = board[x][y] + board[x][y + 2]
                            total += board[x][y]
                            board[x][y + 2] = "_"
                    elif board[x][y + 3] != "_":
                        if board[x][y] == board[x][y + 3]:
                            board[x][y] = board[x][y] + board[x][y + 3]
                            total += board[x][y]
                            board[x][y + 3] = "_"
                except IndexError:
                    pass
            board[x].reverse()
        return board, total

    def check_down(self, board):
        total = 0
        for x in range(len(board)):
            for y in range(len(board[x])):
                try:
                    if board[x][y + 1] != "_":
                        if board[x][y] == board[x][y + 1]:
                            board[x][y] = board[x][y] + board[x][y + 1]
                            total += board[x][y]
                            board[x][y + 1] = "_"
                    elif board[x][y + 2] != "_":
                        if board[x][y] == board[x][y + 2]:
                            board[x][y] = board[x][y] + board[x][y + 2]
                            total += board[x][y]
                            board[x][y + 2] = "_"
                    elif board[x][y + 3] != "_":
                        if board[x][y] == board[x][y + 3]:
                            board[x][y] = board[x][y] + board[x][y + 3]
                            total += board[x][y]
                            board[x][y + 3] = "_"
                except IndexError:
                    pass
        return board, total
