import asyncio
import copy
import random

import discord
from redbot.core import commands


class Minesweeper(commands.Cog):
    """Play Minesweeper inside of Discord"""

    def __init__(self, bot):
        self.bot = bot

    __author__ = "Neuro Assassin#4779 <@473541068378341376>"

    async def red_delete_data_for_user(self, **kwargs):
        """This cog does not store user data"""
        return

    def generate_map(self, max_counter):
        board = [
            ["", "", "", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", "", "", ""],
        ]

        # Pick random spots
        counter = 0
        while counter < max_counter:
            column = random.randint(0, 9)
            row = random.randint(0, 9)
            if board[row][column] == ":bomb:":
                pass
            else:
                board[row][column] = ":bomb:"
                counter += 1

        return board

    def add_hints(self, board):
        for row in range(len(board)):
            for column in range(len(board[row])):
                if board[row][column] == ":bomb:":
                    continue
                hint = 0
                if row == 0 and column == 0:
                    # Check right-most
                    nc = column + 1
                    if board[row][nc] == ":bomb:":
                        hint += 1
                    # Check bottom-right
                    nr = row + 1
                    nc = column + 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check bottom-most
                    nr = row + 1
                    if board[nr][column] == ":bomb:":
                        hint += 1
                elif row == 0 and column == 9:
                    # Check left-most
                    nc = column - 1
                    if board[row][nc] == ":bomb:":
                        hint += 1
                    # Check bottom-left
                    nr = row + 1
                    nc = column - 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check bottom-most
                    nr = row + 1
                    if board[nr][column] == ":bomb:":
                        hint += 1
                elif row == 9 and column == 0:
                    # Check right-most
                    nc = column + 1
                    if board[row][nc] == ":bomb:":
                        hint += 1
                    # Check top-right
                    nr = row - 1
                    nc = column + 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check top-most
                    nr = row - 1
                    if board[nr][column] == ":bomb:":
                        hint += 1
                elif row == 9 and column == 9:
                    # Check left-most
                    nc = column - 1
                    if board[row][nc] == ":bomb:":
                        hint += 1
                    # Check top-left
                    nr = row - 1
                    nc = column - 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check top-most
                    nr = row - 1
                    if board[nr][column] == ":bomb:":
                        hint += 1
                elif row == 0:
                    # Since the first and last positions have already been calculated, I know they are all the same
                    # Check left-most
                    nc = column - 1
                    if board[row][nc] == ":bomb:":
                        hint += 1
                    # Check bottom-left
                    nr = row + 1
                    nc = column - 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check bottom-most
                    nr = row + 1
                    if board[nr][column] == ":bomb:":
                        hint += 1

                    # Check bottom-right
                    nr = row + 1
                    nc = column + 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check right-most
                    nc = column + 1
                    if board[row][nc] == ":bomb:":
                        hint += 1
                elif row == 9:
                    # Check left-most
                    nc = column - 1
                    if board[row][nc] == ":bomb:":
                        hint += 1

                    # Check top-left
                    nr = row - 1
                    nc = column - 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check top-most
                    nr = row - 1
                    if board[nr][column] == ":bomb:":
                        hint += 1

                    # Check top-right
                    nr = row - 1
                    nc = column + 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check right-most
                    nc = column + 1
                    if board[row][nc] == ":bomb:":
                        hint += 1
                elif column == 0:
                    # Check top-most
                    nr = row - 1
                    if board[nr][column] == ":bomb:":
                        hint += 1
                    # Check top-right
                    nr = row - 1
                    nc = column + 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check right-most
                    nc = column + 1
                    if board[row][nc] == ":bomb:":
                        hint += 1

                    # Check bottom-right
                    nr = row + 1
                    nc = column + 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check bottom-most
                    nr = row + 1
                    if board[nr][column] == ":bomb:":
                        hint += 1
                elif column == 9:
                    # Check top-most
                    nr = row - 1
                    if board[nr][column] == ":bomb:":
                        hint += 1
                    # Check top-left
                    nr = row - 1
                    nc = column - 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check left-most
                    nc = column - 1
                    if board[row][nc] == ":bomb:":
                        hint += 1

                    # Check bottom-left
                    nr = row + 1
                    nc = column - 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check bottom-most
                    nr = row + 1
                    if board[nr][column] == ":bomb:":
                        hint += 1
                else:
                    # Check top-most
                    nr = row - 1
                    if board[nr][column] == ":bomb:":
                        hint += 1

                    # Check top-left
                    nr = row - 1
                    nc = column - 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check top-right
                    nr = row - 1
                    nc = column + 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check left-most
                    nc = column - 1
                    if board[row][nc] == ":bomb:":
                        hint += 1

                    # Check right-most
                    nc = column + 1
                    if board[row][nc] == ":bomb:":
                        hint += 1

                    # Check bottom-left
                    nr = row + 1
                    nc = column - 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1

                    # Check bottom-most
                    nr = row + 1
                    if board[nr][column] == ":bomb:":
                        hint += 1

                    # Check bottom-right
                    nr = row + 1
                    nc = column + 1
                    if board[nr][nc] == ":bomb:":
                        hint += 1
                switches = {
                    0: "zero",
                    1: "one",
                    2: "two",
                    3: "three",
                    4: "four",
                    5: "five",
                    6: "six",
                    7: "seven",
                    8: "eight",
                }
                board[row][column] = ":" + str(switches[hint]) + ":"
        return board

    def print_board(self, board):
        whole_thing = ""
        for row in board:
            whole_thing += " ".join(row) + "\n"
        return whole_thing

    def add_desc(self, board):
        nb = copy.deepcopy(board)
        letters = [
            ":regional_indicator_a:",
            ":regional_indicator_b:",
            ":regional_indicator_c:",
            ":regional_indicator_d:",
            ":regional_indicator_e:",
            ":regional_indicator_f:",
            ":regional_indicator_g:",
            ":regional_indicator_h:",
            ":regional_indicator_i:",
            ":regional_indicator_j:",
        ]
        for row in range(len(nb)):
            nb[row].insert(0, letters[row])
        cd = [
            ":black_large_square:",
            ":one:",
            ":two:",
            ":three:",
            ":four:",
            ":five:",
            ":six:",
            ":seven:",
            ":eight:",
            ":nine:",
            ":keycap_ten:",
        ]
        nb.insert(0, cd)
        return nb

    @commands.command(aliases=["ms"])
    async def minesweeper(self, ctx, bombs: int = "Random bomb amount"):
        """Starts a game of minesweeper.

        You can specify the amount of wanted bombs using the bomb paramater.  It must be between 10 bombs and 99 bombs, and defaults to random between 15 to 25."""
        if isinstance(bombs, str):
            bombs = random.randint(15, 25)
        if bombs < 10 or bombs > 99:
            await ctx.send("Amount of bombs must be between 10 and 99.")
            return
        answer_board = self.generate_map(bombs)
        showing_board = []
        for x in range(10):
            showing_board.append(["\u2B1B"] * 10)
        answer_board = self.add_hints(answer_board)
        sending_board = self.add_desc(showing_board)
        sending_board = self.print_board(sending_board)
        bm = await ctx.send(str(sending_board))
        await ctx.send(
            f"Enter the row letter followed by the column number to guess.  The top row is row letter A, and the bottom row is row letter J.  The left column is column number 1, and the right column is column number 10.  For example, a guess could be: 'A1' for the top-left spot of the board, or 'J10' for bottom-right.  Type 'cancel' to stop.  You can guess multiple spots by putting a space between each.  Game will time out after 60 seconds of no response.  The current game has a total of **{bombs}** bombs."
        )
        while bombs > 0:

            def check(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

            try:
                message = await self.bot.wait_for("message", check=check, timeout=60.0)
            except asyncio.TimeoutError:
                await ctx.send("Canceling game due to inactivity.")
                return
            else:
                if message.content == "cancel":
                    await ctx.send("Canceling...")
                    return
                msg = message.content.split(" ")
                to_del = False
                for x in msg:
                    rl = x[0]
                    cn = x[1:]
                    switches = {
                        "a": 0,
                        "b": 1,
                        "c": 2,
                        "d": 3,
                        "e": 4,
                        "f": 5,
                        "g": 6,
                        "h": 7,
                        "i": 8,
                        "j": 9,
                    }
                    try:
                        rn = switches[rl.lower()]
                    except KeyError:
                        continue
                    try:
                        cn = int(cn)
                    except ValueError:
                        continue
                    if cn > 10 or cn <= 0:
                        await ctx.send("Column number is too high or too low.")
                    else:
                        to_del = True
                        cn -= 1
                        if answer_board[rn][cn] == ":bomb:":
                            await ctx.send(
                                f"Uh oh!  {ctx.author.mention} looks like you stumbled across a bomb.  The answer board has been posted above."
                            )
                            answer_board = self.print_board(answer_board)
                            await bm.edit(content=answer_board)
                            return
                        else:
                            showing_board[rn][cn] = answer_board[rn][cn]
                if to_del:
                    try:
                        await message.delete()
                    except (discord.errors.Forbidden, discord.errors.NotFound):
                        pass
                sending_board = self.print_board(self.add_desc(showing_board))
                await bm.edit(content=sending_board)

    @commands.command()
    async def spoilerms(self, ctx, bombs: int = "Random bomb amount"):
        """Starts a non-interactive game of minesweeper with spoilers.
        
        You can specify the amount of wanted bombs using the bomb paramater.  It must be between 10 bombs and 99 bombs, and defaults to random between 15 to 25."""
        if isinstance(bombs, str):
            bombs = random.randint(15, 25)
        if bombs < 10 or bombs > 99:
            await ctx.send("Amount of bombs must be between 10 and 99.")
            return
        answer_board = self.generate_map(bombs)
        answer_board = self.add_hints(answer_board)
        for row in range(len(answer_board)):
            for column in range(len(answer_board[row])):
                answer_board[row][column] = "||" + answer_board[row][column] + "||"
        answer_board = self.print_board(answer_board)
        await ctx.send(answer_board)
        await ctx.send(f"This game has a total of **{bombs}** bombs.")
