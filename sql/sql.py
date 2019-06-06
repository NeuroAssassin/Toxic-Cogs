from redbot.core import commands, checks
from redbot.core.data_manager import cog_data_path
import sqlite3
import traceback
import asyncio
import discord

try:
    from prettytable import PrettyTable

    tableAvailable = True
except ModuleNotFoundError:
    tableAvailable = False


class Sql(commands.Cog):
    """Store data for your guild in SQL format"""

    def __init__(self, bot):
        self.bot = bot

        self.cog_path = cog_data_path(self)

        # Set up databases
        self.memdb = sqlite3.connect(":memory:")
        self.memc = self.memdb.cursor()

        # Set up database settings
        self.memset = sqlite3.connect(str(self.cog_path / "memsettings.sqlite"))
        self.memsetc = self.memset.cursor()

        self.fileset = sqlite3.connect(str(self.cog_path / "filesettings.sqlite"))
        self.filesetc = self.fileset.cursor()

    __author__ = "Neuro Assassin#4779 <@473541068378341376>"

    def cog_unload(self):
        self.__unload()

    def __unload(self):
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

        self.fileset.close()

    @commands.guild_only()
    @commands.group()
    async def sql(self, ctx):
        """Group command for SQL cog.  Warning: due to the input of values, SQL commands are not always sanitized and can result in the destruction of tables on accident.  Run at your own risk."""
        pass

    @checks.admin()
    @sql.group()
    async def settings(self, ctx):
        """Group command for settings management."""
        pass

    @checks.admin()
    @settings.command()
    async def show(self, ctx):
        """Shows the settings of the tables that pertain to your server."""
        await ctx.send("Fetching settings...")
        sent = False
        try:
            self.memsetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
            tables = self.memsetc.fetchall()
            if tableAvailable:
                t = PrettyTable(["Table", "Edit Role", "View Role"])
                for table_data in tables:
                    t.add_row(table_data)
                await ctx.send("**Memory:**\n```py\n" + str(t) + "```")
                sent = True
        except:
            # Hasn't created settings for memory yet
            tables = "ERROR: No tables!"
        finally:
            if not sent:
                await ctx.send("**Memory:**\n```py\n" + str(tables) + "```")
        sent = False
        try:
            self.filesetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
            tables = self.filesetc.fetchall()
            if tableAvailable:
                t = PrettyTable(["Table", "Edit Role", "View Role"])
                for table_data in tables:
                    t.add_row(table_data)
                await ctx.send("**File:**\n```py\n" + str(t) + "```")
                sent = True
        except:
            # Hasn't created settings for file yet
            tables = "ERROR: No tables!"
        finally:
            if not sent:
                await ctx.send("**File:**\n```py\n" + str(tables) + "```")

    @checks.guildowner()
    @settings.command(aliases=["wipe"])
    async def delete(self, ctx, space):
        """Deletes the settings of your tables in either the bot's memory or in your server's file.  Can only be run by guild owner.
        
        Arguments:
            Space: mem |or| file"""
        space = space.lower()
        if space == "mem":
            self.memsetc.execute(f"DROP TABLE IF EXISTS settings{str(ctx.guild.id)}")
        elif space == "file":
            self.filesetc.execute(f"DROP TABLE IF EXISTS settings{str(ctx.guild.id)}")
        else:
            return await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")
        await ctx.send("Settings have been deleted.  Recreating tables...")
        if space == "mem":
            self.memsetc.execute(
                f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name STRING, edit INTEGER, view INTEGER)"
            )
        elif space == "file":
            self.filesetc.execute(
                f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name STRING, edit INTEGER, view INTEGER)"
            )
        await ctx.send("Settings have been recreated.")

    @checks.admin()
    @settings.command(name="update")
    async def settings_update(self, ctx, space, table, edit: int, select: int):
        """Updates a settings entry for a table in the bot's memory or in your server's file.

        Arguments:
            Space: mem |or| file
            Table: name of the table that you are editing the settings for
            Edit: the id of the new role that will be required for editing the table.  Can be 0 if you want anyone to edit data
            Select: the id of the new role that will be required for view data from the table.  Can be 0 if you want anyone to select data"""
        space = space.lower()
        if space == "mem":
            if edit != 0:
                editrole = ctx.guild.get_role(edit)
                if not editrole:
                    return await ctx.send("Invalid edit id.")
            if select != 0:
                selectrole = ctx.guild.get_role(select)
                if not selectrole:
                    return await ctx.send("Invalid select id.")
            try:
                self.memsetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name STRING, edit INTEGER, view INTEGER)"
                )
                self.memsetc.execute(
                    f"UPDATE settings{str(ctx.guild.id)} SET edit=?, view=? WHERE name=?",
                    (edit, select, table),
                )
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your settings failed to be updated because of an error while updating them.  Please notify the owner of the bot about this issues."
                )
                return
            await ctx.send("Your settings have been updated.  Commit to database? (y/n)")

            def check(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

            try:
                message = await self.bot.wait_for("message", check=check, timeout=30.0)
            except asyncio.TimeoutError:
                return await ctx.send("Not committing to database.")
            if message.content.lower().startswith("y"):
                self.memset.commit()
                await ctx.send("Committed to database.")
            else:
                await ctx.send("Not committing to database.")
        elif space == "file":
            if edit != 0:
                editrole = ctx.guild.get_role(edit)
                if not editrole:
                    return await ctx.send("Invalid edit id.")
            if select != 0:
                selectrole = ctx.guild.get_role(select)
                if not selectrole:
                    return await ctx.send("Invalid select id.")
            try:
                self.filesetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name STRING, edit INTEGER, view INTEGER)"
                )
                self.filesetc.execute(
                    f"UPDATE settings{str(ctx.guild.id)} SET edit=?, view=? WHERE name=?",
                    (edit, select, table),
                )
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your settings failed to be updated because of an error while updating them.  Please notify the owner of the bot about this issues."
                )
                return
            await ctx.send("Your settings have been updated.  Commit to database? (y/n)")

            def check(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

            try:
                message = await self.bot.wait_for("message", check=check, timeout=30.0)
            except asyncio.TimeoutError:
                return await ctx.send("Not committing to database.")
            if message.content.lower().startswith("y"):
                self.fileset.commit()
                await ctx.send("Committed to database.")
            else:
                await ctx.send("Not committing to database.")
        else:
            await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")

    @checks.admin()
    @settings.command()
    async def commit(self, ctx, space):
        """Commits changes to the settings database, either the bot's memory's settings or your server's file's settings.

        Arguments:
            Space: mem |or| file"""
        space = space.lower()
        if space == "mem":
            self.memset.commit()
        elif space == "file":
            self.fileset.commit()
        else:
            return await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")
        await ctx.send("Your changes to the settings have been committed.")

    @checks.guildowner()
    @settings.command()
    async def rollback(self, ctx, space):
        """Rolls back changes from the most recent commit, but this is not guaranteed to work.  This is part of the library, so it should be made.

        Arguments:
            Space: mem |or| file"""
        if space == "mem":
            self.memset.rollback()
        elif space == "file":
            self.fileset.rollback()
        else:
            return await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")
        await ctx.send(
            "Your changes to the settings have been attempted to have been rolled back, however, it is possible that they were not."
        )

    @checks.admin()
    @settings.command(name="insert")
    async def settings_insert(self, ctx, table, edit: int, select: int):
        """Inserts a settings entry into the table in case it failed to be made during `[p]sql create` or if the table was made using `[p]sql execute`.  However, you cannot create for memory databases through this because of effects with other tables.

        Arguments:
            Table: name of the table you are creating settings for
            Edit: id of the role that is required for editing the table.  Can be 0 if you want anyone to edit data
            Select: id of the role that is required for viewing/selecting the table.  Can be 0 if you want anyone to select data"""
        filedb = sqlite3.connect(str(self.cog_path / f"{str(ctx.guild.id)}db.sqlite"))
        filec = filedb.cursor()
        filec.execute("SELECT name FROM sqlite_master WHERE type= 'table'")
        tables = filec.fetchall()[0]
        if not (table in tables):
            return await ctx.send("That table is not registered in your server's database file.")
        if edit != 0:
            editrole = ctx.guild.get_role(edit)
            if not editrole:
                return await ctx.send("Invalid edit id.")
        if select != 0:
            selectrole = ctx.guild.get_role(select)
            if not selectrole:
                return await ctx.send("Invalid select id.")
        try:
            self.filesetc.execute(
                f"INSERT INTO settings{str(ctx.guild.id)} VALUES (?,?,?)", (table, edit, select)
            )
        except Exception as e:
            await ctx.send(
                "Error while running sql command:\n```py\n"
                + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                + "```"
            )
            await ctx.send(
                "Your entry failed to be insert into settings because of an error while doing so.  Please notify the owner of the bot about this issues."
            )
            return
        await ctx.send("Your data has been inserted into settings.  Commit to database? (y/n)")

        def check(m):
            return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

        try:
            message = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("Not committing to database.")
        if message.content.lower().startswith("y"):
            self.fileset.commit()
            await ctx.send("Committed to database.")
        else:
            await ctx.send("Not committing to database.")
        filedb.close()

    @sql.command(aliases=["remove"])
    async def deleteentry(self, ctx, space, table, category, *value):
        """Removes a row from a table in either memory or the server's file.  Only users with the edit role specified when making the table can run this command.  Does sanitize data inputs.

        Arguments:
            Space: mem |or| file
            Table: name of table you're editing
            Category: name of the category of which you'll be specifying a value to choose a certain row
            Value: the value that is in the category of the row you want to delete"""
        await ctx.send("Verifying authority...")
        if space == "mem":
            try:
                self.memsetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)"
                )
                self.memsetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.memsetc.fetchall()
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your row failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues."
                )
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    return await ctx.send("That table does not exist.")
                roles = [role.id for role in ctx.author.roles]
                roles.append(0)
                if int(table_settings[1]) in roles:
                    await ctx.send("Permissions confirmed.  Deleting row from table table...")
                else:
                    await ctx.send(
                        "You do not have permission to delete data from this table.  Please contact someone who has the appropriate edit role in order to delete data from this table."
                    )
                    return
                command = "DELETE FROM " + table + " WHERE " + category + "=?"
                try:
                    self.memc.execute(command, value)
                except Exception as e:
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    await ctx.send(
                        "Your data failed to be deleted because of an error while deleting it.  Please notify the owner of the bot about this issue."
                    )
                else:
                    await ctx.send(
                        f"The data with the value of `{value[0]}` in the `{category}` category in the `{table}` table has been deleted from memory.  Commit to database? (y/n)"
                    )

                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

                    try:
                        message = await self.bot.wait_for("message", check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not committing to database.")
                        return
                    if message.content.lower().startswith("y"):
                        self.memdb.commit()
                        await ctx.send("Committed to database.")
                    else:
                        await ctx.send("Not committing to database.")
        elif space == "file":
            filedb = sqlite3.connect(str(self.cog_path / f"{str(ctx.guild.id)}db.sqlite"))
            filec = filedb.cursor()
            try:
                self.filesetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)"
                )
                self.filesetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.filesetc.fetchall()
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your row failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues."
                )
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    return await ctx.send("That table does not exist.")
                roles = [role.id for role in ctx.author.roles]
                roles.append(0)
                if int(table_settings[1]) in roles:
                    await ctx.send("Permissions confirmed.  Deleting row from table...")
                else:
                    await ctx.send(
                        "You do not have permission to delete data from this table.  Please contact someone who has the appropriate edit role in order to delete data from this table."
                    )
                    return
                command = "DELETE FROM " + table + " WHERE " + category + "=?"
                try:
                    filec.execute(command, value)
                except Exception as e:
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    await ctx.send(
                        "Your data failed to be deleted because of an error while deleting it.  Please notify the owner of the bot about this issue."
                    )
                else:
                    await ctx.send(
                        f"The data with the value of `{value[0]}` in the `{category}` category in the `{table}` table has been deleted from your server's database.  Commit to database? (y/n)"
                    )

                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

                    try:
                        message = await self.bot.wait_for("message", check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not committing to database.")
                        return
                    if message.content.lower().startswith("y"):
                        filedb.commit()
                        await ctx.send("Committed to database.")
                    else:
                        await ctx.send("Not committing to database.")
                    filedb.close()
        else:
            await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")

    @sql.command()
    async def update(self, ctx, space, table, category, value, *values):
        """Updates an entry in a table either in the bot's memory or your server's file.  You must have the edit role that was specified in the making in the table to run this.  Does sanitize data inputs.

        Arguments:
            Space: mem |or| file
            Table: The name of the table you wish to update
            Category + value: describes where your making the change.  The catgory is the column and the value is the value of the column of the row you want to replace
            Values: Values to replace the current row's values
        """
        await ctx.send("Verifying authority...")
        if space == "mem":
            try:
                self.memsetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)"
                )
                self.memsetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.memsetc.fetchall()
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your table failed to be updated because of an error while checking settings.  Please notify the owner of the bot about this issues."
                )
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    return await ctx.send("That table does not exist.")
                roles = [role.id for role in ctx.author.roles]
                roles.append(0)
                if int(table_settings[1]) in roles:
                    await ctx.send("Permissions confirmed.  Updating data...")
                else:
                    await ctx.send(
                        "You do not have permission to update data in this table.  Please contact someone who has the appropriate edit role in order to update data in this table."
                    )
                    return
                self.memc.execute(f"PRAGMA table_info({table})")
                columns = self.memc.fetchall()
                command = "UPDATE " + table + " SET "
                for column in range(len(columns)):
                    try:
                        command += columns[column][1] + "='" + values[columns[column][0]] + "'"
                        if column != len(columns) - 1:
                            command += ", "
                    except IndexError:
                        await ctx.send(
                            "Not enough values were provided to update the row in the table."
                        )
                        return
                command += " WHERE " + category + "=?"
                try:
                    self.memc.execute(command, (value,))
                except Exception as e:
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    await ctx.send(
                        "Your data failed to be updated into the table because of an error while inserting it.  Please notify the owner of the bot about this issue."
                    )
                else:
                    await ctx.send(
                        f"The data `{str(values)}` has been inserted into the table `{table}` (updated a row).  Commit to database? (y/n)"
                    )

                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

                    try:
                        message = await self.bot.wait_for("message", check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not committing to database.")
                        return
                    if message.content.lower().startswith("y"):
                        self.memdb.commit()
                        await ctx.send("Committed to database.")
                    else:
                        await ctx.send("Not committing to database.")
        elif space == "file":
            filedb = sqlite3.connect(str(self.cog_path / f"{str(ctx.guild.id)}db.sqlite"))
            filec = filedb.cursor()
            try:
                self.filesetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)"
                )
                self.filesetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.filesetc.fetchall()
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your table failed to be updated because of an error while checking settings.  Please notify the owner of the bot about this issues."
                )
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    return await ctx.send("That table does not exist.")
                roles = [role.id for role in ctx.author.roles]
                roles.append(0)
                if int(table_settings[1]) in roles:
                    await ctx.send("Permissions confirmed.  Updating data...")
                else:
                    await ctx.send(
                        "You do not have permission to update data in this table.  Please contact someone who has the appropriate edit role in order to update data in this table."
                    )
                    return
                filec.execute(f"PRAGMA table_info({table})")
                columns = filec.fetchall()
                command = "UPDATE " + table + " SET "
                for column in range(len(columns)):
                    try:
                        command += columns[column][1] + "='" + values[columns[column][0]] + "'"
                        if column != len(columns) - 1:
                            command += ", "
                    except IndexError:
                        await ctx.send(
                            "Not enough values were provided to update the row in the table."
                        )
                        return
                command += " WHERE " + category + "=?"
                try:
                    filec.execute(command, (value,))
                except Exception as e:
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    await ctx.send(
                        "Your data failed to be updated into the table because of an error while inserting it.  Please notify the owner of the bot about this issue."
                    )
                else:
                    await ctx.send(
                        f"The data `{str(values)}` has been inserted into the table `{table}` (updated a row).  Commit to database? (y/n)"
                    )

                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

                    try:
                        message = await self.bot.wait_for("message", check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not committing to database.")
                        return
                    if message.content.lower().startswith("y"):
                        filedb.commit()
                        await ctx.send("Committed to database.")
                    else:
                        await ctx.send("Not committing to database.")
                    filedb.close()
        else:
            await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")

    @sql.command(name="all", aliases=["show"])
    async def allt(self, ctx, space):
        """Returns all tables in either the bot's memory or your server's file.  However, the list of tables in memory is taken from the memory settings, so you can't see other server's tables in memory.
        
        Arguments:
            Space: mem |or| file"""
        if space == "mem":
            self.memsetc.execute(
                f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name STRING, edit INTEGER, view INTEGER)"
            )
            self.memsetc.execute(f"SELECT name FROM settings{str(ctx.guild.id)}")
            tables = self.memsetc.fetchall()
            if tableAvailable:
                t = PrettyTable(["Table"])
                for table_data in tables:
                    t.add_row(table_data)
                await ctx.send(f"All tables in memory:```python\n{str(t)}```")
            else:
                await ctx.send(f"All tables in memory:```python\n{str(tables)}```")
        elif space == "file":
            filedb = sqlite3.connect(str(self.cog_path / f"{str(ctx.guild.id)}db.sqlite"))
            filec = filedb.cursor()
            filec.execute("SELECT name FROM sqlite_master WHERE type= 'table'")
            tables = filec.fetchall()
            if tableAvailable:
                t = PrettyTable(["Table"])
                for table_data in tables:
                    t.add_row(table_data)
                await ctx.send(f"All tables in server file:```python\n{str(t)}```")
            else:
                await ctx.send(f"All tables in server file:```python\n{str(tables)}```")
            filedb.close()
        else:
            await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")

    @sql.command()
    async def insert(self, ctx, space, table, *values):
        """Inserts data into a table.  Can only be run by users with the edit role that is specified in the table settings.  Does sanitize data inputs.

        Arguments:
            Space: mem |or| file
            Table: name of the table you wish to insert data into
            Values: the data you wish to insert into the table, in column order"""
        await ctx.send("Verifying authority...")
        if space == "mem":
            try:
                self.memsetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)"
                )
                self.memsetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.memsetc.fetchall()
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your data failed to be inserted into the table because of an error while checking settings.  Please notify the owner of the bot about this issues."
                )
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    return await ctx.send("That table does not exist.")
                roles = [role.id for role in ctx.author.roles]
                roles.append(0)
                if int(table_settings[1]) in roles:
                    await ctx.send("Permissions confirmed.  Inserting data...")
                else:
                    await ctx.send(
                        "You do not have permission to insert data into this table.  Please contact someone who has the appropriate edit role in order to insert data into this table."
                    )
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
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    await ctx.send(
                        "Your data failed to be inserted into the table because of an error while inserting it.  Please notify the owner of the bot about this issue."
                    )
                else:
                    await ctx.send(
                        f"The data `{str(values)}` has been inserted into the table `{table}`.  Commit to database? (y/n)"
                    )

                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

                    try:
                        message = await self.bot.wait_for("message", check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not committing to database.")
                        return
                    if message.content.lower().startswith("y"):
                        self.memdb.commit()
                        await ctx.send("Committed to database.")
                    else:
                        await ctx.send("Not committing to database.")
        elif space == "file":
            filedb = sqlite3.connect(str(self.cog_path / f"{str(ctx.guild.id)}db.sqlite"))
            filec = filedb.cursor()
            try:
                self.filesetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)"
                )
                self.filesetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.filesetc.fetchall()
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your data failed to be inserted into the table because of an error while checking settings.  Please notify the owner of the bot about this issues."
                )
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    return await ctx.send("That table does not exist.")
                roles = [role.id for role in ctx.author.roles]
                roles.append(0)
                if int(table_settings[1]) in roles:
                    await ctx.send("Permissions confirmed.  Inserting data...")
                else:
                    await ctx.send(
                        "You do not have permission to insert data into this table.  Please contact someone who has the appropriate edit role in order to insert data into this table."
                    )
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
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    await ctx.send(
                        "Your data failed to be inserted into the table because of an error while inserting it.  Please notify the owner of the bot about this issue."
                    )
                else:
                    await ctx.send(
                        f"The data `{str(values)}` has been inserted into the table `{table}`.  Commit to database? (y/n)"
                    )

                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

                    try:
                        message = await self.bot.wait_for("message", check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not committing to database.")
                        return
                    if message.content.lower().startswith("y"):
                        filedb.commit()
                        await ctx.send("Committed to database.")
                    else:
                        await ctx.send("Not committing to database.")
                    filedb.close()
        else:
            await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")

    @sql.command(name="view", aliases=["see", "select"])
    async def select(self, ctx, space, table, category="", value=""):
        """Views data from a table, with a condition able to be specified.  Only people who have the role to view the table can perform this command.  Does sanitize data inputs.

        If you wish to see a certain entry, you can specify the category and the value you want the category to be using the last two arguments.
        
        Arguments:
            Space: mem |or| file
            Table: the table from which you'd like to read data
            Category (optional): the name of the category of the value you are specifying
            Value (optional): value of the column of the row of which you'd like to select data from"""
        await ctx.send("Verifying authority...")
        if space == "mem":
            try:
                self.memsetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)"
                )
                self.memsetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.memsetc.fetchall()
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your table failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues."
                )
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    return await ctx.send("That table does not exist.")
                roles = [role.id for role in ctx.author.roles]
                roles.append(0)
                if int(table_settings[2]) in roles:
                    await ctx.send("Permissions confirmed")
                else:
                    await ctx.send(
                        "You do not have permission to view data from this table.  Please contact someone who has the appropriate edit role in order to view this table."
                    )
                    return
                if category == "":
                    command = "SELECT * FROM " + table
                    extra = False
                else:
                    if value == "":
                        await ctx.send(
                            "You provided a column, but not a value for the column.  Cannot perform sql command."
                        )
                        return
                    command = "SELECT * FROM " + table + " WHERE " + category + "=?"
                    extra = True
                try:
                    if extra:
                        self.memc.execute(command, (value,))
                    else:
                        self.memc.execute(command)
                except Exception as e:
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    await ctx.send(
                        "Failed to fetch data from the table.  Please make sure you put in a correct category."
                    )
                    return
                data = self.memc.fetchall()
                if tableAvailable:
                    self.memc.execute(f"PRAGMA table_info({table})")
                    columns = self.memc.fetchall()
                    setting_columns = ["Row Number"]
                    for entry in range(len(columns)):
                        setting_columns.append(columns[entry][1])
                    t = PrettyTable(setting_columns)
                    counter = 1
                    new_data = []
                    for x in data:
                        stuff = []
                        for y in x:
                            stuff.append(y)
                        new_data.append(stuff)
                    for row_data in new_data:
                        row_data.insert(0, counter)
                        t.add_row(row_data)
                        counter += 1
                    await ctx.send(
                        f"Command completed successfully.  Data returned from command: ```python\n{str(t)}```"
                    )
                    return
                await ctx.send(
                    f"Command completed successfully.  Data returned from command: ```python\n{str(data)}```"
                )
        elif space == "file":
            filedb = sqlite3.connect(str(self.cog_path / f"{str(ctx.guild.id)}db.sqlite"))
            filec = filedb.cursor()
            try:
                self.filesetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)"
                )
                self.filesetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.filesetc.fetchall()
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your table failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues."
                )
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    return await ctx.send("That table does not exist.")
                roles = [role.id for role in ctx.author.roles]
                roles.append(0)
                if int(table_settings[2]) in roles:
                    await ctx.send("Permissions confirmed")
                else:
                    await ctx.send(
                        "You do not have permission to view data from this table.  Please contact someone who has the appropriate edit role in order to view this table."
                    )
                    return
                if category == "":
                    command = "SELECT * FROM " + table
                    extra = False
                else:
                    if value == "":
                        await ctx.send(
                            "You provided a column, but not a value for the column.  Cannot perform sql command."
                        )
                        return
                    command = "SELECT * FROM " + table + " WHERE " + category + "=?"
                    extra = True
                try:
                    if extra:
                        filec.execute(command, (value,))
                    else:
                        filec.execute(command)
                except Exception as e:
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    await ctx.send(
                        "Failed to fetch data from the table.  Please make sure you put in a correct category."
                    )
                    return
                data = filec.fetchall()
                if tableAvailable:
                    filec.execute(f"PRAGMA table_info({table})")
                    columns = filec.fetchall()
                    setting_columns = ["Row Number"]
                    for entry in range(len(columns)):
                        setting_columns.append(columns[entry][1])
                    t = PrettyTable(setting_columns)
                    counter = 1
                    new_data = []
                    for x in data:
                        stuff = []
                        for y in x:
                            stuff.append(y)
                        new_data.append(stuff)
                    for row_data in new_data:
                        row_data.insert(0, counter)
                        t.add_row(row_data)
                        counter += 1
                    await ctx.send(
                        f"Command completed successfully.  Data returned from command: ```python\n{str(t)}```"
                    )
                    filedb.close()
                    return
                filedb.close()
                await ctx.send(
                    f"Command completed successfully.  Data returned from command: ```python\n{str(data)}```"
                )
        else:
            await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")

    @sql.command(name="delete", aliases=["drop"])
    async def tabledelete(self, ctx, space, table):
        """Deletes a table in the certain space.  Only people who have the role to edit the table can perform this command.  Does not sanitize data inputs.

        Arguments:
            Space: mem |or| file
            Table: name of the table of which you'd like to delete"""
        await ctx.send("Verifying authority...")
        if space == "mem":
            try:
                self.memsetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)"
                )
                self.memsetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.memsetc.fetchall()
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your table failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues."
                )
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    return await ctx.send("That table does not exist.")
                roles = [role.id for role in ctx.author.roles]
                roles.append(0)
                if int(table_settings[1]) in roles:
                    await ctx.send("Permissions confirmed.  Deleting table...")
                else:
                    await ctx.send(
                        "You do not have permission to delete this table.  Please contact someone who has the appropriate edit role in order to delete this table."
                    )
                    return
                command = "DROP TABLE " + table
                try:
                    self.memc.execute(command)
                except Exception as e:
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    await ctx.send(
                        "Your table failed to be deleted because of an error while deleting it.  Please notify the owner of the bot about this issue."
                    )
                else:
                    await ctx.send(
                        f"The `{table}` table has been deleted from your server's database.  Deleting table settings..."
                    )
                    try:
                        self.memsetc.execute(
                            f"DELETE FROM settings{str(ctx.guild.id)} WHERE name=?", (table,)
                        )
                    except Exception as e:
                        await ctx.send(
                            "Error while running sql command:\n```py\n"
                            + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                            + "```"
                        )
                        await ctx.send(
                            "Your table was deleted, but the entry for this table failed to be deleted from the settings table.  Please notify the owner of the bot about this issue."
                        )
                        return
                    await ctx.send(
                        "Your table has been deleted and the settings have been updated.  Commit to database? (y/n)"
                    )

                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

                    try:
                        message = await self.bot.wait_for("message", check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not committing to database.")
                        return
                    if message.content.lower().startswith("y"):
                        self.memdb.commit()
                        self.memset.commit()
                        await ctx.send("Committed to database.")
                    else:
                        await ctx.send("Not committing to database.")
        elif space == "file":
            filedb = sqlite3.connect(str(self.cog_path / f"{str(ctx.guild.id)}db.sqlite"))
            filec = filedb.cursor()
            try:
                self.filesetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name TEXT, edit INTEGER, view INTEGER)"
                )
                self.filesetc.execute(f"SELECT * FROM settings{str(ctx.guild.id)}")
                settings = self.filesetc.fetchall()
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your table failed to be deleted because of an error while checking settings.  Please notify the owner of the bot about this issues."
                )
                return
            else:
                table_settings = None
                for entry in settings:
                    if entry[0] == table:
                        table_settings = entry
                        break
                if table_settings == None:
                    return await ctx.send("That table does not exist.")
                roles = [role.id for role in ctx.author.roles]
                roles.append(0)
                if int(table_settings[1]) in roles:
                    await ctx.send("Permissions confirmed.  Deleting table...")
                else:
                    await ctx.send(
                        "You do not have permission to delete this table.  Please contact someone who has the appropriate edit role in order to delete this table."
                    )
                    return
                command = "DROP TABLE " + table
                try:
                    filec.execute(command)
                except Exception as e:
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    await ctx.send(
                        "Your table failed to be deleted because of an error while deleting it.  Please notify the owner of the bot about this issue."
                    )
                else:
                    await ctx.send(
                        f"The `{table}` table has been deleted from your server's database.  Deleting table settings..."
                    )
                    try:
                        self.filesetc.execute(
                            f"DELETE FROM settings{str(ctx.guild.id)} WHERE name=?", (table,)
                        )
                    except Exception as e:
                        await ctx.send(
                            "Error while running sql command:\n```py\n"
                            + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                            + "```"
                        )
                        await ctx.send(
                            "Your table was deleted, but the entry for this table failed to be deleted from the settings table.  Please notify the owner of the bot about this issue."
                        )
                        return
                    await ctx.send(
                        "Your table has been deleted and the settings have been updated.  Commit to database? (y/n)"
                    )

                    def check(m):
                        return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

                    try:
                        message = await self.bot.wait_for("message", check=check, timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Not committing to database.")
                        return
                    if message.content.lower().startswith("y"):
                        filedb.commit()
                        self.fileset.commit()
                        await ctx.send("Committed to database.")
                    else:
                        await ctx.send("Not committing to database.")
                    filedb.close()
        else:
            await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")

    @checks.admin()
    @sql.command()
    async def create(self, ctx, space, edit: int, select: int, name):
        """Creates a table in either the file or memory database.  Can only be run by administrators.  Provide the id of the role that is necessary to edit it and the id of the role necessary to select/view values from the table. Does not sanitize data inputs.

        Arguments:
            Space: mem |or| file
            Edit: id of the role that is required to edit data from this table.  Can be 0 if you wish for anyone to edit it
            Select: id of the role that is required to select/view data from this table.  Can be 0 if you wish for anyone to select it
            Name: name of the table of which you'd like to create"""
        await ctx.send("Entering Interactive Mode for Creating Table...")
        await ctx.send(
            "For every category in you want in the server, type the name of the category and then the type.  For example, 'string text' or 'id integer'.  Type 'exit' to exit interactive mode."
        )

        def check(m):
            return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

        nex = ""
        categories = []
        while nex != "exit":
            try:
                message = await self.bot.wait_for("message", check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send("Interactive mode timed out.  Exiting.")
                return
            nex = message.content
            if nex != "exit":
                categories.append(nex)
                await ctx.send("Category noted.  Type your next category or type 'exit'")
        command = "CREATE TABLE " + name + "(" + ", ".join(categories) + ")"
        if edit != 0:
            editrole = ctx.guild.get_role(edit)
            if not editrole:
                return await ctx.send("Invalid edit role.")
        if select != 0:
            selectrole = ctx.guild.get_role(select)
            if not selectrole:
                return await ctx.send("Invalid select role.")
        if space == "mem":
            try:
                self.memc.execute(command)
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                return
            await ctx.send("The CREATE TABLE command has been run.  Updating settings table...")
            try:
                self.memsetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name STRING, edit INTEGER, view INTEGER)"
                )
                self.memsetc.execute(
                    f"INSERT INTO settings{str(ctx.guild.id)}(name, edit, view) VALUES(?,?,?)",
                    (name, edit, select),
                )
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your table has been created, but settings have not been registered and changes have not been committed."
                )
                return
            await ctx.send("The settings table has been updated.  Commit to database? (y/n)")

            def check2(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

            try:
                message = await self.bot.wait_for("message", check=check2, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send("Not committing to database.")
                return
            if message.content.lower().startswith("y"):
                self.memdb.commit()
                self.memset.commit()
                await ctx.send("Committed to database.")
            else:
                await ctx.send("Not committing to database.")
        elif space == "file":
            filedb = sqlite3.connect(str(self.cog_path / f"{ctx.guild.id}db.sqlite"))
            filec = filedb.cursor()
            try:
                filec.execute(command)
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                return
            await ctx.send("The CREATE TABLE command has been run.  Updating settings table...")
            try:
                self.filesetc.execute(
                    f"CREATE TABLE IF NOT EXISTS settings{str(ctx.guild.id)}(name STRING, edit INTEGER, view INTEGER)"
                )
                self.filesetc.execute(
                    f"INSERT INTO settings{str(ctx.guild.id)}(name, edit, view) VALUES(?,?,?)",
                    (name, edit, select),
                )
            except Exception as e:
                await ctx.send(
                    "Error while running sql command:\n```py\n"
                    + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    + "```"
                )
                await ctx.send(
                    "Your table has been created, but settings have not been registered and changes have not been committed."
                )
                return
            await ctx.send("The settings table has been updated.  Commit to database? (y/n)")

            def check2(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

            try:
                message = await self.bot.wait_for("message", check=check2, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send("Not committing to database.")
                return
            if message.content.lower().startswith("y"):
                filedb.commit()
                self.fileset.commit()
                await ctx.send("Committed to database.")
            else:
                await ctx.send("Not committing to database.")
            filedb.close()
        else:
            await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")

    @checks.guildowner()
    @sql.command()
    async def execute(self, ctx, space: str, ret: str, *, command):
        """Executes a raw sql command safely.
        The command can be run in either the bot's memory db or in your server's file db.  The bot's memory lasts until the next reboot, while the file db is permanent.  For setting the return values, use 'n' if you do not want anything returned, but if you do, use 'yall' to get all or 'yone' to get one.  Does not sanitize data inputs.

        This command is discouraged unless this is necessary.  While creating tables, settings are not registered for it, and the owner bypasses every permission.  If settings are needed, they will need to be set manually.
        
        Arguments:
            Space: mem |or| file
            Ret: whether to return value; n if not, y if so (add 'all' for all data to be returned or 'one' if you'd like only one piece of the data returned
            Command: command to be run"""
        await ctx.send(
            "**Warning!**  This command is discouraged from use.  It is recommended to use to prebuilt commands unless you have to use this.  When creating tables, settings are not registered.  That is heavily discouraged.\nWould you like to proceed?  (y/n)"
        )

        def check(m):
            return (
                (m.author.id == ctx.author.id)
                and (m.content.lower()[0] in ["y", "n"])
                and (m.channel.id == ctx.channel.id)
            )

        try:
            message = await self.bot.wait_for("message", check=check, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.send("Canceling command due to lack of response.")
            return
        else:
            if message.content.lower().startswith("y"):
                await ctx.send("Continuing...")
            else:
                return await ctx.send(
                    "Canceling command due to improper response/declination of warning."
                )
        if space == "mem":
            if ret.startswith("y"):
                try:
                    self.memc.execute(command)
                    if ret[1:] == "all":
                        value = self.memc.fetchall()
                    elif ret[1:] == "one":
                        value = self.memc.fetchone()
                    else:
                        return await ctx.send("Return value argument invalid.")
                except Exception as e:
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    return
                else:
                    await ctx.send("Value returned from command:\n```py\n" + str(value) + "```")
            else:
                try:
                    self.memc.execute(command)
                except Exception as e:
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    return
                else:
                    pass
            await ctx.send("Command has been run.  Commit to database? (y/n)")

            def check2(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

            try:
                message = await self.bot.wait_for("message", check=check2, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send("Not committing to database.")
                return
            if message.content.lower().startswith("y"):
                self.memdb.commit()
                await ctx.send("Committed to database.")
            else:
                await ctx.send("Not committing to database.")
        elif space == "file":
            filedb = sqlite3.connect(str(self.cog_path / f"{ctx.guild.id}db.sqlite"))
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
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    return
                else:
                    await ctx.send("Value returned from command:\n```py\n" + str(value) + "```")
            else:
                try:
                    filec.execute(command)
                except Exception as e:
                    await ctx.send(
                        "Error while running sql command:\n```py\n"
                        + "".join(traceback.format_exception(type(e), e, e.__traceback__))
                        + "```"
                    )
                    return
                else:
                    pass
            await ctx.send("Command has been run.  Commit to database? (y/n)")

            def check3(m):
                return (m.author.id == ctx.author.id) and (m.channel.id == ctx.channel.id)

            try:
                message = await self.bot.wait_for("message", check=check3, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send("Not committing to database.")
                return
            if message.content.lower().startswith("y"):
                filedb.commit()
                await ctx.send("Committed to database.")
            else:
                await ctx.send("Not committing to database.")
            filedb.close()
        else:
            await ctx.send("Invalid `space` argument.  Please use 'mem' or 'file'.")

    @sql.command(name="help")
    async def _help(self, ctx):
        """Provides information about the cog, because I know this cog seems confusing"""
        await ctx.send(
            (
                "Hello there.  Thank you for downloading this cog.  Here are some tips on how to use it:\n\n"
                "This cog is primarily for the storing of data in sql format.  You can store whatever you want in them.  For example, you can store your favorite singers, warnings for users and a bunch of other stuff!\n"
                "**Now that we've said what it can do, here's some tips:**\n"
                "    1. While there is a command to run straight up sql commands (only for guild owners), I strongly suggest not using it.  It is better to use the shortcut commands since they also create settings for tables and permission checks.\n"
                "    2. When tables are created using `[p]sql create`, a settings entry is also registered for it on your server's database settings.  This allows you to control who can edit data from the table and who can view data in the table.\n"
                "    3. It is recommended to create tables in your server's file database, instead of the bot's memory.  This is because tables created in the bot's memory can be affected by other guild owners by using `[p]sql execute`.  However, your server's file is completely safe.\n"
                "    4. When a command asks for the 'space', you can reply with `mem` or `file.`  Entering `mem` puts/searches in the bot's memory, while `file` puts/searches in your server's database file.\n"
                "    5. Right now, with tables, you can create them, delete them, insert data into them, update data in them, delete data from them and also view data from them.\n"
                "    6. Right now, with settings, you can view them, delete them (strongly discouraged), insert setting entries and update setting entries.\n"
                "    7. I mentioned above that it is recommended to use pre-built commands, mostly because of settings.  If you create a table without settings, no one access them through any commands.  The only way to access the table would be through `[p]sql execute`.\n"
                "Well, I hope that makes you understand the SQL cog a bit more.  Hope it turns out to help!"
            )
        )
        await ctx.send(
            "*If you need help, don't hesitate to join my support server here: https://discord.gg/vQZTdB9*"
        )
