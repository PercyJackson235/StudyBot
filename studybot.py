#!/home/user/dev/StudyBot/venv/bin/python3
from discord.ext import commands
from discord import Status
import sqlite3
import asyncio
from contextlib import closing
from typing import Union
from datetime import datetime


def get_tokens():
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv('DISCORD_TOKEN'), os.getenv('DISCORD_GUILD')


command_list = []
help_dict = {"add-time": "Add the personal amount of study time in minutes.",
             "get-time": "Retrieves the personal amount of hours studied.",
             "all-time": "Retrieves the total amount of study time.",
             "shutdown": "Shuts down the Bot. Need bot-admin.",
             "start-timer": "Starts study timer.",
             "stop-timer": "Stops study timer.",
             "verify-study": "Verify the amount of study time: true or false."}


def _command_list_adder(func):
    command_list.append(func)
    return func


def proper_role(self, rolename: str = "bot-admin"):
    for role in self.author.roles:
        if rolename in role.name:
            return True
    return False


def log_writer(err: Exception, filename: str = "error.log"):
    with open(filename, 'a') as f:
        f.write("{}\n".format(repr(err)))


def proper_channel(bot_channel: str, channels: Union[list, tuple]):
    for channel in channels:
        if bot_channel == channel.name:
            return True
    return False


async def invalid_channel(request: commands.Context, bot: commands.Bot):
    if request.channel.name != bot._channel_name:
        args = (type(bot).__name__, request.channel.name, bot._channel_name)
        await request.reply("{} doesn't respond on {}, only {}".format(*args))
        return True
    return False


class StudyBot(commands.Bot):
    _command_list = command_list

    def __init__(self, *args, **kwargs):
        self._db_conn = sqlite3.connect("server.db")
        self._lock = asyncio.Lock()
        self._bot_stop = False
        self._channel_name = "bot-channel"
        self._bot_channel()
        super().__init__(*args, **kwargs)
        with closing(self._db_conn.cursor()) as conn:
            table = 'CREATE TABLE IF NOT EXISTS study_time '
            table += '(name text, minutes integer, server text)'
            conn.execute(table)
            self._db_conn.commit()
            table = 'CREATE TABLE IF NOT EXISTS live_timer '
            table += '(name text, server text, timestamp real)'
            conn.execute(table)
            self._db_conn.commit()
        for func in self._command_list:
            self.add_command(func)

    def _bot_channel(self, write: bool = False):
        file = "channel.txt"
        if write:
            with open(file, 'w') as f:
                f.write(self._channel_name)
        else:
            import os
            if not os.path.exists(file):
                return
            with open(file, 'r') as f:
                self._channel_name = f.read().strip()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._db_conn.commit()
        self._db_conn.close()
        if not self.is_closed():
            self.logout()
        self._bot_channel(self._channel_name)

    async def on_ready(self):
        await self.change_presence(status=Status.online)
        for server in self.guilds:
            for channel in server.channels:
                if channel.name == self._channel_name:
                    msg = "{} is online.".format(self.user)
                    await channel.send(msg)
                    return

    @_command_list_adder
    @commands.command(help=help_dict.get('shutdown'))
    async def shutdown(self):
        # Commands are context objects and have bot as an object
        if await invalid_channel(self, self.bot):
            return
        if proper_role(self):
            text = "Okay. I, {}, am shutting down"
            await self.bot.change_presence(status=Status.offline)
            await self.reply(text.format(self.bot.user))
            await asyncio.sleep(10)
            await self.bot.logout()
            await self.close()
            return
        msg = "Sorry, you must have the bot-admin role to shutdown this bot."
        await self.reply(msg, delete_after=15)
        await self.close()

    @_command_list_adder
    @commands.command(name="set-channel")
    async def set_channel(self, name: str):
        if await invalid_channel(self, self.bot):
            return
        if name not in (i.name for i in self.channel.guild.channels):
            await self.reply("{} is not a channel on this server".format(name))
            return
        if proper_role(self):
            self.bot._channel_name = name
            await self.reply("{} is set as the StudyBot Channel.".format(name))
        else:
            await self.reply("You do not have the right to change the Channel")

    @_command_list_adder
    @commands.command(name="add-time", help=help_dict.get('add-time'))
    async def add_time(self, minutes: Union[int, str] = 0):
        if await invalid_channel(self, self.bot):
            return
        if self.channel.name != self.bot._channel_name:
            args = (type(self.bot).__name__, self.channel.name, self.bot._channel_name)  # noqa: E501
            await self.reply("{} doesn't respond on {}, only {}".format(*args))
            return
        if isinstance(minutes, str):
            if not minutes.isdigit():
                await self.reply("'{}' is not a proper value".format(minutes))
                return
            minutes = int(minutes)
        if minutes < 0:
            await self.reply("'{}' is not a proper value".format(minutes))
            return
        msg = "Added {} hours and {} minutes."
        username = str(self.author)
        with closing(self.bot._db_conn.cursor()) as conn:
            async with self.bot._lock:
                query = 'SELECT minutes FROM study_time WHERE name = ? AND server = ?'  # noqa: E501
                conn.execute(query, (username, str(self.guild)))
                if conn.fetchone() is None:
                    query = 'INSERT INTO study_time (name, minutes, server)'
                    query += ' VALUES (?, ?, ?)'
                    conn.execute(query, (username, 0, str(self.guild)))
                query = 'UPDATE study_time SET minutes = minutes + ? '
                query += 'WHERE name = ? AND server = ?'
                conn.execute(query, (minutes, username, str(self.guild)))
                self.bot._db_conn.commit()
        try:
            await self.reply(msg.format(*divmod(minutes, 60)))  # noqa: E501
        except Exception as e:
            log_writer(e)

    @_command_list_adder
    @commands.command(name="get-time", help=help_dict.get('get-time'))
    async def get_time(self):
        if await invalid_channel(self, self.bot):
            return
        if self.channel.name != self.bot._channel_name:
            args = (type(self.bot).__name__, self.channel.name, self.bot._channel_name)  # noqa: E501
            await self.reply("{} doesn't respond on {}, only {}".format(*args))
            return
        username = str(self.author)
        with closing(self.bot._db_conn.cursor()) as conn:
            async with self.bot._lock:
                query = 'SELECT minutes FROM study_time WHERE name = ? AND server = ?'  # noqa: E501
                conn.execute(query, (username, str(self.guild)))
                value = conn.fetchone()
                if value is None:
                    query = 'INSERT INTO study_time (name, minutes, server) '
                    query += 'VALUES (?, ?, ?)'
                    conn.execute(query, (username, 0, str(self.guild)))
                    query = 'SELECT minutes FROM study_time WHERE name = ? AND server = ?'  # noqa: E501
                    conn.execute(query, (username, str(self.guild)))
                    value = conn.fetchone()[0]
                else:
                    value = value[0]
                msg = "You have contributed {} hours and {} minutes to total."
                await self.reply(msg.format(*divmod(value, 60)))
                self.bot._db_conn.commit()

    @_command_list_adder
    @commands.command(name="all-time", help=help_dict.get('all-time'))
    async def all_time(self):
        if await invalid_channel(self, self.bot):
            return
        if self.channel.name != self.bot._channel_name:
            args = (type(self.bot).__name__, self.channel.name, self.bot._channel_name)  # noqa: E501
            await self.reply("{} doesn't respond on {}, only {}".format(*args))
            return
        with closing(self.bot._db_conn.cursor()) as conn:
            async with self.bot._lock:
                query = 'SELECT minutes FROM study_time WHERE server = ?'
                conn.execute(query, (str(self.guild),))
                value = sum(i[0] for i in conn.fetchall())
                msg = "The total amount of time studying is {} hours"
                msg += " and {} minutes."
                await self.reply(msg.format(*divmod(value, 60)))
                self.bot._db_conn.commit()

    @_command_list_adder
    @commands.command(name="start-timer", help=help_dict.get('start-timer'))
    async def start_study(self):
        if await invalid_channel(self, self.bot):
            return
        if self.channel.name != self.bot._channel_name:
            args = (type(self.bot).__name__, self.channel.name, self.bot._channel_name)  # noqa: E501
            await self.reply("{} doesn't respond on {}, only {}".format(*args))
            return
        timestamp = datetime.now().timestamp()
        username, server = map(str, (self.author, self.guild))
        with closing(self.bot._db_conn.cursor()) as conn:
            async with self.bot._lock:
                query = 'SELECT timestamp FROM live_timer WHERE name = ? AND server = ?'
                conn.execute(query, (username, server))
                result = conn.fetchone()
                if result is None:
                    query = 'INSERT INTO live_timer (name, server, timestamp) '
                    query += 'VALUES (?, ?, ?)'
                    conn.execute(query, (username, server, timestamp))
                elif result[0] == 0.0:
                    query = 'UPDATE live_timer SET timestamp = ? '
                    query += 'WHERE name = ? AND server = ?'
                    conn.execute(query, (timestamp, username, server))
                elif bool(result[0]):
                    await self.reply("Already started timer.", delete_after=120)
                    self.bot._db_conn.commit()
                    return
                else:
                    await self.reply("Sorry. Unexpected Error happend.")
                    err = "In start_study, result is not None, 0.0, or timestamp."
                    err += f"Username = {username}, Server = {server}, "
                    err += f"timestamp = {timestamp}." 
                    log_writer(err)
                    self.bot._db_conn.commit()
                    return
        await self.reply("Okay. Started Timer.", delete_after=120)
        self.bot._db_conn.commit()

    @_command_list_adder
    @commands.command(name="stop-timer", help=help_dict.get('stop-timer'))
    async def stop_study(self):
        if await invalid_channel(self, self.bot):
            return
        if self.channel.name != self.bot._channel_name:
            args = (type(self.bot).__name__, self.channel.name, self.bot._channel_name)  # noqa: E501
            await self.reply("{} doesn't respond on {}, only {}".format(*args))
            return
        username, server = map(str, (self.author, self.guild))
        result = 0.0
        minutes = 0
        with closing(self.bot._db_conn.cursor()) as conn:
            async with self.bot._lock:
                query = 'SELECT timestamp FROM live_timer WHERE name = ? '
                query += 'AND server = ?'
                conn.execute(query, (username, server))
                result = conn.fetchone()
                if result is None:
                    await self.reply("Never started timer.", delete_after=120)
                    self.bot._db_conn.commit()
                    return
                elif result[0] == 0.0:
                    await self.reply("Never started timer.", delete_after=120)
                    self.bot._db_conn.commit()
                    return
                elif bool(result[0]):
                    result = datetime.now() - datetime.fromtimestamp(result[0])
                    minutes, seconds = divmod(result.seconds, 60)
                    minutes += round(seconds / 60)
                    query = 'UPDATE live_timer SET timestamp = ? '
                    query += 'WHERE name = ? AND server = ?'
                    conn.execute(query, (float(minutes), username, server))
                else:
                    await self.reply("Sorry. Unexpected Error happend.")
                    err = "In stop_study, result is not None, 0.0, or timestamp."
                    err += f"Username = {username} and Server = {server}"
                    log_writer(err)
                    self.bot._db_conn.commit()
                    return
        msg = "Timer is stopped. Please '!verify-study True' if {} minutes is"
        msg += " the proper amount of study time. If false please '!verify-"
        msg += "study False'."
        await self.reply(msg.format(minutes), delete_after=300)
        self.bot._db_conn.commit()

    @_command_list_adder
    @commands.command(name="verify-study", help=help_dict.get("verify-study"))
    async def verify(self, value: bool):
        if await invalid_channel(self, self.bot):
            return
        if self.channel.name != self.bot._channel_name:
            args = (type(self.bot).__name__, self.channel.name, self.bot._channel_name)  # noqa: E501
            await self.reply("{} doesn't respond on {}, only {}".format(*args))
            return
        username, server = map(str, (self.author, self.guild))
        msg = "Added {} hours and {} minutes."
        minutes = 0
        with closing(self.bot._db_conn.cursor()) as conn:
            async with self.bot._lock:
                if value:
                    query = 'SELECT timestamp FROM live_timer WHERE name = ? '
                    query += 'AND server = ?'
                    conn.execute(query, (username, server))
                    result = conn.fetchone()
                    if result[0] is None:
                        errormsg = "Timer was never set. Cannot verify."
                        await self.reply(errormsg, delete_after=60)
                        self.bot._db_conn.commit()
                        return
                    elif result[0] == 0.0:
                        errormsg = "Timer was never set. Cannot verify."
                        await self.reply(errormsg, delete_after=60)
                        self.bot._db_conn.commit()
                        return
                    elif bool(result[0]):
                        if divmod(result[0], 1)[1] != 0.0:
                            msg = "Timer was never stopped. Cannot verify."
                            await self.reply(msg)
                            self.bot._db_conn.commit()
                            return
                        result = minutes = int(result[0])
                        query = 'UPDATE study_time SET minutes = minutes + ? '
                        query += 'WHERE name = ? AND server = ?'
                        conn.execute(query, (result, username, server))
                        query = 'UPDATE live_timer SET timestamp = ? '
                        query += 'WHERE name = ? AND server = ?'
                        conn.execute(query, (0.0, username, server))
                    else:
                        await self.reply("Sorry. Unexpected Error happend.")
                        msg = f"verify_study. Username = {username} and "
                        msg += f"Server = {server}"
                        log_writer(msg)
                        self.bot._db_conn.commit()
                        return
                else:
                    msg = "Okay. Discarding recorded study time."
                    await self.reply(msg, delete_after=30)
                    query = 'UPDATE live_timer SET timestamp = ? '
                    query += 'WHERE name = ? AND server = ?'
                    conn.execute(query, (0.0, username, server))
                    return
        self.bot._db_conn.commit()
        await self.reply(msg.format(*divmod(minutes, 60)))


if __name__ == "__main__":
    with StudyBot("!") as bot:
        bot.run(get_tokens()[0])
