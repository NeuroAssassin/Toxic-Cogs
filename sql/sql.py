from redbot.core import commands, checks
from redbot.core.data_manager import bundled_data_path
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

        #self.filedb = sqlite3.connect("sqldb.sqlite")
        #self.filec = self.filedb.cursor()

        # Set up database settings
        self.memset = sqlite3.connect(str(bundled_data_path(self)) + "/memsettings.sqlite")
        self.memsetc = self.memset.cursor()

        self.fileset = sqlite3.connect(str(bundled_data_path(self)) + "/filesettings.sqlite")
        self.filesetc = self.fileset.cursor()

        # Create settings tables
        #self.memsetc.execute("CREATE TABLE IF NOT EXISTS settings(name STRING, server INTEGER, edit INTEGER, view INTEGER)")
        #self.memset.commit()

        #self.filesetc.execute("CREATE TABLE IF NOT EXISTS settings(name STRING, server INTEGER, edit INTEGER, view INTEGER)")
        #self.fileset.commit()

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
        self.memsetc.execute("SELECT name FROM sqlite_master WHERE type= 'table'")
        tables = self.memsetc.fetchall()
        for table in tables:
            try:
                self.memsetc.execute("DROP TABLE " + table[0])
            except:
                pass
        self.memset.commit()
        self.memset.close()

    @commands.group()
    async def sql(self, ctx):
        """Group command for SQL cog.  Warning: due to the input of values, SQL commands are not sanitized and can result in the destruction of tables on accident.  Run at your own risk."""
        pass

    @sql.group()
    async def settings(self, ctx):
        """Group command for settings management"""

    @checks.admin()
    @settings.command()
    async def show(self, ctx):
        await ctx.send("Fetching settings...")
        try:
            self.memsetc.execute(f'SELECT * FROM settings{str(ctx.guild.id)}')
            tables = self.memsetc.fetchall()
        except:
            # Hasn't created settings for memory yet
            tables = "ERROR: No tables!"
        await ctx.send("**Memory:**\n```py\n" + str(tables) + "```")
        try:
            self.filesetc.execute(f'SELECT * FROM settings{str(ctx.guild.id)}')
            tables = self.filesetc.fetchall()
        except:
            # Hasn't created settings for file yet
            tables = "ERROR: No tables!"
        await ctx.send("**File:**\n```py\n" + str(tables) + "```")

    @checks.admin()
    @settings.command()
    async def delete(self, ctx, space):
        if space == "mem":
            self.memsetc.execute(f"DROP TABLE IF EXISTS settings{str(ctx.guild.id)}")
        elif space == "file":
            self.filesetc.execute(f"DROP TABLE IF EXISTS settings{str(ctx.guild.id)}")
        await ctx.send("Settings have been deleted.  Recreating tables...")
        if space == "mem":
            self.memsetc.execute(f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name STRING, edit INTEGER, view INTEGER)")
        elif space == "file":
            self.filesetc.execute(f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name STRING, edit INTEGER, view INTEGER)")
        await ctx.send("Settings have been recreated.")

    @sql.command()
    async def insert(self, ctx, space, table, *values):
        """Inserts data into a table.  Can only be run by users with the edit role that is specified in the table settings"""
        await ctx.send("Verifying authority...")
        if space == "mem":
            try:
                self.memsetc.execute(f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)")
                self.memsetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.memsetc.fetchall()
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                await ctx.send("Your table failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues.")
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    await ctx.send("That table does not exist.")
                    return
                if int(table_settings[1]) in [role.id for role in ctx.author.roles]:
                    await ctx.send("Permissions confirmed.  Inserting data...")
                else:
                    await ctx.send("You do not have permission to insert data into this table.  Please contact someone who has the appropriate edit role in order to insert data into this table.")
                    return
                command = "INSERT INTO " + table + " VALUES("
                for x in range(len(values)):
                    command += "?"
                    if x != len(values) - 1:
                        command += ","
                command += ")"
                try:
                    self.memc.execute(command, values)
                except Exception as e:
                    await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                    await ctx.send("Your data failed to be inserted into the table because of an error while inserting it.  Please notify the owner of the bot about this issue.")
                else:
                    await ctx.send("The data `" + str(values) + "` has been inserted into the table `" + table + "`.  Commit to database? (y/n)")
                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
                    try:
                        message = await self.bot.wait_for('message', check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not commiting to database.")
                        return
                    if message.content.lower().startswith('y'):
                        self.memdb.commit()
                        self.memset.commit()
                        await ctx.send("Commited to database.")
                    else:
                        await ctx.send("Not commiting to database.")
        elif space == "file":
            filedb = sqlite3.connect(str(bundled_data_path(self)) + f"/{str(ctx.guild.id)}db.sqlite")
            filec = filedb.cursor()
            try:
                self.filesetc.execute(f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)")
                self.filesetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.filesetc.fetchall()
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                await ctx.send("Your table failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues.")
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    await ctx.send("That table does not exist.")
                    return
                if int(table_settings[1]) in [role.id for role in ctx.author.roles]:
                    await ctx.send("Permissions confirmed.  Inserting data...")
                else:
                    await ctx.send("You do not have permission to insert data into this table.  Please contact someone who has the appropriate edit role in order to insert data into this table.")
                    return
                command = "INSERT INTO " + table + " VALUES("
                for x in range(len(values)):
                    command += "?"
                    if x != len(values) - 1:
                        command += ","
                command += ")"
                try:
                    filec.execute(command, values)
                except Exception as e:
                    await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                    await ctx.send("Your data failed to be inserted into the table because of an error while inserting it.  Please notify the owner of the bot about this issue.")
                else:
                    await ctx.send("The data `" + str(values) + "` has been inserted into the table `" + table + "`.  Commit to database? (y/n)")
                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
                    try:
                        message = await self.bot.wait_for('message', check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not commiting to database.")
                        return
                    if message.content.lower().startswith('y'):
                        filedb.commit()
                        await ctx.send("Commited to database.")
                    else:
                        await ctx.send("Not commiting to database.")
                    filedb.close()

    @sql.command(name="view", aliases=["see", "select"])
    async def select(self, ctx, space, table, category="", value=""):
        """Views data from a table, with a condition able to be specified.  Only people who have the role to view the table can perform this command.
        
        If you wish to see a certain entry, you can specify the category and the value you want the category to be using the last two arguments.
        """
        await ctx.send("Verifying authority...")
        if space == "mem":
            try:
                self.memsetc.execute(f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)")
                self.memsetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.memsetc.fetchall()
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                await ctx.send("Your table failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues.")
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    await ctx.send("That table does not exist.")
                    return
                if int(table_settings[2]) in [role.id for role in ctx.author.roles]:
                    await ctx.send("Permissions confirmed")
                else:
                    await ctx.send("You do not have permission to view data from this table.  Please contact someone who has the appropriate edit role in order to view this table.")
                    return
                if category == "":
                    command = "SELECT * FROM " + table
                else:
                    command = "SELECT * FROM " + table + " WHERE " + category + "='" + value + "'"
                try:
                    self.memc.execute(command)
                except Exception as e:
                    await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                    await ctx.send("Failed to fetch data from the table.  Please make sure you put in a correct category.")
                    return
                data = self.memc.fetchall()
                await ctx.send("Command completed successfully.  Data returned from command: ```python\n" + str(data) + "```")
        elif space == "file":
            filedb = sqlite3.connect(str(bundled_data_path(self)) + f"/{str(ctx.guild.id)}db.sqlite")
            filec = filedb.cursor()
            try:
                self.filesetc.execute(f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)")
                self.filesetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.filesetc.fetchall()
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                await ctx.send("Your table failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues.")
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    await ctx.send("That table does not exist.")
                    return
                if int(table_settings[2]) in [role.id for role in ctx.author.roles]:
                    await ctx.send("Permissions confirmed")
                else:
                    await ctx.send("You do not have permission to view data from this table.  Please contact someone who has the appropriate edit role in order to view this table.")
                    return
                if category == "":
                    command = "SELECT * FROM " + table
                else:
                    command = "SELECT * FROM " + table + " WHERE " + category + "='" + value + "'"
                try:
                    filec.execute(command)
                except Exception as e:
                    await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                    await ctx.send("Failed to fetch data from the table.  Please make sure you put in a correct category.")
                    return
                data = filec.fetchall()
                filedb.close()
                await ctx.send("Command completed successfully.  Data returned from command: ```python\n" + str(data) + "```")
    

    @sql.command(name="delete", aliases=["drop"])
    async def tabledelete(self, ctx, space, table):
        """Deletes a table in the certain space.  Only people who have the role to edit the table can perform this command."""
        await ctx.send("Verifying authority...")
        if space == "mem":
            try:
                self.memsetc.execute(f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)")
                self.memsetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.memsetc.fetchall()
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                await ctx.send("Your table failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues.")
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    await ctx.send("That table does not exist.")
                    return
                if int(table_settings[1]) in [role.id for role in ctx.author.roles]:
                    await ctx.send("Permissions confirmed.  Deleting table...")
                else:
                    await ctx.send("You do not have permission to delete this table.  Please contact someone who has the appropriate edit role in order to delete this table.")
                    return
                command = "DROP TABLE " + table
                try:
                    self.memc.execute(command)
                except Exception as e:
                    await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                    await ctx.send("Your table failed to be deleted because of an error while deleting it.  Please notify the owner of the bot about this issue.")
                else:
                    await ctx.send("The `" + table + "` table has been deleted from your server's database.  Deleting table settings...")
                    try:
                        self.memsetc.execute(f"DELETE FROM settings{str(ctx.guild.id)} WHERE name=?", (table,))
                    except Exception as e:
                        await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                        await ctx.send("Your table was deleted, but the entry for this table failed to be deleted from the settings table.  Please notify the owner of the bot about this issue.")
                        return
                    await ctx.send("Your table has been deleted and the settings have been updated.  Commit to database? (y/n)")
                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
                    try:
                        message = await self.bot.wait_for('message', check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not commiting to database.")
                        return
                    if message.content.lower().startswith('y'):
                        self.memdb.commit()
                        self.memset.commit()
                        await ctx.send("Commited to database.")
                    else:
                        await ctx.send("Not commiting to database.")
        elif space == "file":
            filedb = sqlite3.connect(str(bundled_data_path(self)) + f"/{str(ctx.guild.id)}db.sqlite")
            filec = filedb.cursor()
            try:
                self.filesetc.execute(f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)")
                self.filesetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.filesetc.fetchall()
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                await ctx.send("Your table failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues.")
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    await ctx.send("That table does not exist.")
                    return
                if int(table_settings[1]) in [role.id for role in ctx.author.roles]:
                    await ctx.send("Permissions confirmed.  Deleting table...")
                else:
                    await ctx.send("You do not have permission to delete this table.  Please contact the server owner in order to delete this table.")
                    return
                command = "DROP TABLE " + table
                try:
                    filec.execute(command)
                except Exception as e:
                    await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                    await ctx.send("Your table failed to be deleted because of an error while deleting it.  Please notify the owner of the bot about this issue.")
                else:
                    await ctx.send("The `" + table + "` table has been deleted from your server's database.  Deleting table settings...")
                    try:
                        self.filesetc.execute(f"DELETE FROM settings{str(ctx.guild.id)} WHERE name=?", (table,))
                    except Exception as e:
                        await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                        await ctx.send("Your table was deleted, but the entry for this table failed to be deleted from the settings table.  Please notify the owner of the bot about this issue.")
                        return
                    await ctx.send("Your table has been deleted and the settings have been updated.  Commit to database? (y/n)")
                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
                    try:
                        message = await self.bot.wait_for('message', check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not commiting to database.")
                        return
                    if message.content.lower().startswith('y'):
                        filedb.commit()
                        self.fileset.commit()
                        await ctx.send("Commited to database.")
                    else:
                        await ctx.send("Not commiting to database.")
                    filedb.close()

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
                await ctx.send("Category noted.  Type your next category or type 'exit'")
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
                self.memsetc.execute(f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name STRING, edit INTEGER, view INTEGER)")
                self.memsetc.execute(f'INSERT INTO settings{str(ctx.guild.id)}(name, edit, view) VALUES(?,?,?)', (name, edit, select))
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                await ctx.send("Your table has been created, but settings have not been registered and changes have not been committed.  Run [p]sql commit to commit these changes.")
                return
            await ctx.send("The settings table has been updated.  Commit to database? (y/n)")
            def check2(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
            try:
                message = await self.bot.wait_for('message', check=check2, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send("Not commiting to database.")
                return
            if message.content.lower().startswith('y'):
                self.memdb.commit()
                self.memset.commit()
                await ctx.send("Commited to database.")
            else:
                await ctx.send("Not commiting to database.")
        elif space == "file":
            filedb = sqlite3.connect(str(bundled_data_path(self)) + f"/{ctx.guild.id}db.sqlite")
            filec = filedb.cursor()
            try:
                filec.execute(command)
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                return
            await ctx.send("The CREATE TABLE command has been run.  Updating settings table...")
            try:
                self.filesetc.execute(f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name STRING, edit INTEGER, view INTEGER)")
                self.filesetc.execute(f'INSERT INTO settings{str(ctx.guild.id)}(name, edit, view) VALUES(?,?,?)', (name, edit, select))
            except Exception as e:
                await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                await ctx.send("Your table has been created, but settings have not been registered and changes have not been committed.  Run [p]sql commit to commit these changes.")
                return
            await ctx.send("The settings table has been updated.  Commit to database? (y/n)")
            def check2(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
            try:
                message = await self.bot.wait_for('message', check=check2, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send("Not commiting to database.")
                return
            if message.content.lower().startswith('y'):
                filedb.commit()
                self.fileset.commit()
                await ctx.send("Committed to database.")
            else:
                await ctx.send("Not commiting to database.")
            filedb.close()
        

    @checks.guildowner()
    @sql.command()
    async def execute(self, ctx: commands.context, space: str, ret: str, *, command):
        """Executes a raw sql command safely.
        The command can be run in either the bot's memory db or in your server's file db.  The bot's memory lasts until the next reboot, while the file db is permanent.  For setting the return values, use 'n' if you do not want anything returned, but if you do, use 'yall' to get all or 'yone' to get one.

        This command is discouraged unless this is necessary.  While creating tables, settings are not registered for it, and the owner bypasses every permission.  If settings are needed, they will need to be set manually."""
        await ctx.send("**Warning!**  This command is discouraged from use.  It is recommended to use to prebuilt commands unless you have to use this.  When creating tables, settings are not registered.  That is heavily discouraged.\nWould you like to proceed?  (y/n)")
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
            try:
                message = await self.bot.wait_for('message', check=check2, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send("Not commiting to database.")
                return
            if message.content.lower().startswith('y'):
                self.memdb.commit()
                await ctx.send("Commited to database.")
            else:
                await ctx.send("Not commiting to database.")
        elif space == "file":
            filedb = sqlite3.connect(str(bundled_data_path(self)) + f"/{ctx.guild.id}db.sqlite")
            filec = filedb.cursor()
            if ret.startswith("y"):
                try:
                    filec.execute(command)
                    if ret[1:] == "all":
                        value = filec.fetchall()
                    elif ret[1:] == "one":
                        value = filec.fetchone()
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
                    filec.execute(command)
                except Exception as e:
                    await ctx.send("Error while running sql command:\n```py\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)) + "```")
                    return
                else:
                    pass
            await ctx.send("Command has been run.  Commit to database? (y/n)")
            def check3(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)
            try:
                message = await self.bot.wait_for('message', check=check3, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send("Not commiting to database.")
                return
            if message.content.lower().startswith('y'):
                filedb.commit()
                await ctx.send("Commited to database.")
            else:
                await ctx.send("Not commiting to database.")
            filedb.close()
