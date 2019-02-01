from redbot.core import commands, checks
import sqlite3
import traceback
import asyncio

#BaseCog = getattr(commands, "Cog", object)

class Sql(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Set up databases
        self.memdb = sqlite3.connect(":memory:")
        self.memc = self.memdb.cursor()

        self.filedb = sqlite3.connect("sqldb.sqlite")
        self.filec = self.filedb.cursor()

        # Set up database settings
        self.memset = sqlite3.connect("memsettings.sqlite")
        self.memsetc = self.memset.cursor()

        self.fileset = sqlite3.connect("filesettings.sqlite")
        self.filesetc = self.fileset.cursor()

        # Create settings tables
        self.memsetc.execute("CREATE TABLE IF NOT EXISTS settings(name STRING, edit INTEGER, view INTEGER)")
        self.memset.commit()

        self.filesetc.execute("CREATE TABLE IF NOT EXISTS settings(name STRING, edit INTEGER, view INTEGER)")
        self.fileset.commit()

    def __unload(self):
        print("In __unload")

        # Delete tables from memory
        self.memc.execute("SELECT name FROM sqlite_master WHERE type= 'table'")
        tables = self.memc.fetchall()
        for table in tables:
            try:
                self.memc.execute("DROP TABLE " + table[0])
            except:
                pass
        self.memdb.commit()
        self.memdb.close()

        # Destroy settings
        self.memsetc.execute("DROP TABLE settings")
        self.memset.commit()
        self.memset.close()

    @commands.group()
    async def sql(self, ctx):
        """Group command for SQL cog.  Warning: due to the input of values, SQL commands are not sanitized and can result in the destruction of tables on accident.  Run at your own risk."""
        pass

    @checks.admin()
    @sql.command()
    async def settings(self, ctx):
        await ctx.send("Fetching settings...")
        self.memsetc.execute('SELECT * FROM settings')
        tables = self.memsetc.fetchall()
        await ctx.send("**Memory:**\n```py\n" + str(tables) + "```")
        self.filesetc.execute('SELECT * FROM settings')
        tables = self.filesetc.fetchall()
        await ctx.send("**File:**\n```py\n" + str(tables) + "```")

    @checks.admin()
    @sql.command()
    async def create(self, ctx, space, edit: int, select: int, name):
        """Creates a table in either the file or memory database.  Can only be run by administrators.  Provide the id of the role that is necessary to edit it and the id of the role necessary to select/view values from the table."""
        await ctx.send("Entering Interactive Mode for Creating Table...")
        await ctx.send("For every category in you want in the server, type the name of the category and then the type.  For example, 'string text' or 'id integer'.  Type 'exit' to exit interactive mode.")
        def check(m):
            return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
        nex = ""
        categories = []
        while nex != "exit":
            message = await self.bot.wait_for('message', check=check)
            nex = message.content
            if nex != "exit":
                categories.append(nex)
        command = "CREATE TABLE " + name + "(" + ", ".join(categories) + ")"
        editrole = ctx.guild.get_role(edit)
        selectrole = ctx.guild.get_role(select)
        if not (editrole and selectrole):
            await ctx.send("Cannot perform create table command, invalid role ids.")
            return
        if space == "mem":
            try:
                self.memc.execute(command)
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                return
            await ctx.send("The CREATE TABLE command has been run.  Updating settings table...")
            try:
                self.memsetc.execute('INSERT INTO settings(name, edit, view) VALUES(?,?,?)', (name, edit, select))
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                await ctx.send("Your table has been created, but settings have not been registered and changes have not been committed.  Run [p]sql commit to commit these changes.")
                return
            await ctx.send("The settings table has been updated.  Commit to database? (y/n)")
            def check2(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
            message = await self.bot.wait_for('message', check=check2, timeout=30.0)
            if message.content.lower().startswith('y'):
                self.memdb.commit()
                self.memset.commit()
                await ctx.send("Commited to database.")
            else:
                await ctx.send("Not commiting to database.")
        elif space == "file":
            try:
                self.filec.execute(command)
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                return
            await ctx.send("The CREATE TABLE command has been run.  Updating settings table...")
            try:
                self.filesetc.execute('INSERT INTO settings(name, edit, view) VALUES(?,?,?)', (name, edit, select))
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                await ctx.send("Your table has been created, but settings have not been registered and changes have not been committed.  Run [p]sql commit to commit these changes.")
                return
            await ctx.send("The settings table has been updated.  Commit to database? (y/n)")
            def check2(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
            message = await self.bot.wait_for('message', check=check2, timeout=30.0)
            if message.content.lower().startswith('y'):
                self.filedb.commit()
                self.fileset.commit()
                await ctx.send("Committed to database.")
            else:
                await ctx.send("Not commiting to database.")
        

    @checks.is_owner()
    @sql.command()
    async def execute(self, ctx: commands.context, space: str, ret: str, *, command):
        """Executes a raw sql command safely.
        The command can be run in either the bot's memory db or in the bot's file db.  The bot's memory lasts until the next reboot, while the file db is permanent.

        This command is discouraged unless this is necessary.  While creating tables, settings are not registered for it, and the owner bypasses every permission.  If settings are needed, they will need to be set manually."""
        await ctx.send("**Warning!**  This command is discouraged from use.  It is recommended to use to prebuilt commands unless you have to use this.  When creating tables, settings are not registered  That is heavily discouraged.\nWould you like to proceed?  (y/n)")
        def check(m):
            return (m.author.id == ctx.author.id) and (m.content.lower().startswith('y') or m.content.lower().startswith('n')) and (m.channel.id == ctx.channel.id)
        try:
            message = await self.bot.wait_for('message', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.send("Canceling command due to lack of response.")
            return
        else:
            if message.content.lower().startswith('y'):
                await ctx.send("Continuing...")
            else:
                await ctx.send("Canceling command due to improper response/declination of warning.")
                return
        if space == "mem":
            if ret.startswith("y"):
                try:
                    self.memc.execute(command)
                    if ret[1:] == "all":
                        value = self.memc.fetchall()
                    elif ret[1:] == "one":
                        value = self.memc.fetchone()
                    else:
                        await ctx.send("Return value argument invalid.")
                        return
                except Exception as e:
                    await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                    return
                else:
                    await ctx.send("Value returned from command:\n```py\n" + str(value) + "```")
            else:
                try:
                    self.memc.execute(command)
                except Exception as e:
                    await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                    return
                else:
                    pass
            await ctx.send("Command has been run.  Commit to database? (y/n)")

            def check2(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
            message = await self.bot.wait_for('message', check=check2, timeout=30.0)
            if message.content.lower().startswith('y'):
                self.memdb.commit()
                await ctx.send("Commited to database.")
            else:
                await ctx.send("Not commiting to database.")
        elif space == "file":
            if ret.startswith("y"):
                try:
                    self.filec.execute(command)
                    if ret[1:] == "all":
                        value = self.filec.fetchall()
                    elif ret[1:] == "one":
                        value = self.filec.fetchone()
                    else:
                        await ctx.send("Return value argument invalid.")
                        return
                except Exception as e:
                    await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                    return
                else:
                    await ctx.send("Value returned from command:\n```py\n" + str(value) + "```")
            else:
                try:
                    self.filec.execute(command)
                except Exception as e:
                    await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                    return
                else:
                    pass
            await ctx.send("Command has been run.  Commit to database? (y/n)")
            def check3(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
            message = await self.bot.wait_for('message', check=check3, timeout=30.0)
            if message.content.lower().startswith('y'):
                self.filedb.commit()
                await ctx.send("Commited to database.")
            else:
                await ctx.send("Not commiting to database.")
