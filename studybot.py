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


def proper_channel(bot_channel: str, channels: Union[list, tuple]):
    for channel in channels:
        if bot_channel == channel.name:
            return True
    return False


class StudyBot(commands.Bot):
    _command_list = command_list

    def __init__(self, *args, **kwargs):
        self._db_conn = sqlite3.connect("server.db")
        self._lock = asyncio.Lock()
        self._time_dict: dict[tuple, Union[datetime, int]] = {}
        self._channel_name = "bot-channel"
        self._bot_channel()
        super().__init__(*args, **kwargs)
        with closing(self._db_conn.cursor()) as conn:
            table = 'CREATE TABLE IF NOT EXISTS study_time '
            table += '(name text, minutes integer, server text)'
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
        print(self, type(self), dir(self))

    @_command_list_adder
    @commands.command(help=help_dict.get('shutdown'))
    async def shutdown(self):
        # Commands are context objects and have bot as an object
        if self.channel.name != self.bot._channel_name:
            args = (type(self.bot).__name__, self.channel.name, self.bot._channel_name)  # noqa: E501
            await self.reply("{} doesn't respond on {}, only {}".format(*args))
            return
        if proper_role(self):
            text = "Okay. I, {}, am shutting down"
            await self.bot.change_presence(status=Status.offline)
            await self.reply(text.format(self.bot.user))
            await asyncio.sleep(10)
            await self.bot.logout()
            return
        msg = "Sorry, you must have the bot-admin role to shutdown this bot."
        await self.reply(msg, delete_after=15)

    @_command_list_adder
    @commands.command(name="set-channel")
    async def set_channel(self, name: str):
        for i in (self.channel.guild.channels, self.channel.guild):
            print(dir(i), i)
        if name not in (i.name for i in self.channel.guild.channels):
            await self.reply("{} is not a channel on this server".format(name))
            return
        if proper_role(self):
            self.bot._channel_name = name
            await self.reply("{} is set as the StudyBot Channel.".format(name))

    @_command_list_adder
    @commands.command(name="add-time", help=help_dict.get('add-time'))
    async def add_time(self, minutes: Union[int, str] = 0):
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
            print(repr(e))

    @_command_list_adder
    @commands.command(name="get-time", help=help_dict.get('get-time'))
    async def get_time(self):
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
        if self.channel.name != self.bot._channel_name:
            args = (type(self.bot).__name__, self.channel.name, self.bot._channel_name)  # noqa: E501
            await self.reply("{} doesn't respond on {}, only {}".format(*args))
            return
        key = tuple(map(str, (self.author, self.channel, self.guild)))
        if key in self.bot._time_dict:
            msg = "You have already started the timer. Please end timer "
            msg += "before starting another."
            await self.reply(msg, delete_after=120)
            return
        self.bot._time_dict[key] = datetime.now()
        await self.reply("Okay. Started Timer.", delete_after=120)
        print(self.bot._time_dict)

    @_command_list_adder
    @commands.command(name="stop-timer", help=help_dict.get('stop-timer'))
    async def stop_study(self):
        if self.channel.name != self.bot._channel_name:
            args = (type(self.bot).__name__, self.channel.name, self.bot._channel_name)  # noqa: E501
            await self.reply("{} doesn't respond on {}, only {}".format(*args))
            return
        key = tuple(map(str, (self.author, self.channel, self.guild)))
        if key not in self.bot._time_dict:
            msg = "You have not started a timer. Please start one."
            await self.reply(msg, delete_after=60)
            return
        elif isinstance(self.bot._time_dict[key], int):
            msg = "Timer is not running. Either verify time or start timer."
            await self.reply(msg, delete_after=60)
            return
        result = datetime.now() - self.bot._time_dict[key]
        minutes, seconds = divmod(result.seconds, 60)
        minutes += round(seconds / 60)
        self.bot._time_dict[key] = minutes
        msg = "Timer is stopped. Please '!verify-study True' if {} minutes is"
        msg += " the proper amount of study time. If false please '!verify-"
        msg += "study False'."
        await self.reply(msg.format(minutes), delete_after=300)
        print(self.bot._time_dict)

    @_command_list_adder
    @commands.command(name="verify-study", help=help_dict.get("verify-study"))
    async def verify(self, value: bool):
        if self.channel.name != self.bot._channel_name:
            args = (type(self.bot).__name__, self.channel.name, self.bot._channel_name)  # noqa: E501
            await self.reply("{} doesn't respond on {}, only {}".format(*args))
            return
        key = tuple(map(str, (self.author, self.channel, self.guild)))
        if value:
            username, guild = str(self.author), str(self.guild)
            msg = "Added {} hours and {} minutes."
            minutes = self.bot._time_dict.get(key)
            if minutes is None:
                errormsg = "Timer was never set. Cannot verify."
                await self.reply(errormsg, delete_after=60)
                return
            elif not isinstance(minutes, int):
                errormsg = "Timer was never stopped. Cannot verify."
                await self.reply(errormsg, delete_after=60)
                return
            with closing(self.bot._db_conn.cursor()) as conn:
                async with self.bot._lock:
                    query = 'SELECT minutes FROM study_time WHERE name = ? AND server = ?'  # noqa: E501
                    conn.execute(query, (username, guild))
                    if conn.fetchone() is None:
                        query = 'INSERT INTO study_time (name, minutes, server)'  # noqa: E501
                        query += ' VALUES (?, ?, ?)'
                        conn.execute(query, (username, 0, guild))
                    query = 'UPDATE study_time SET minutes = minutes + ? '
                    query += 'WHERE name = ? AND server = ?'
                    conn.execute(query, (minutes, username, guild))
                    self.bot._db_conn.commit()
            try:
                await self.reply(msg.format(*divmod(minutes, 60)))  # noqa: E501
            except Exception as e:
                print(repr(e))
        else:
            msg = "Okay. Discarding recorded study time."
            await self.reply(msg, delete_after=30)
        del self.bot._time_dict[key]
        print(self.bot._time_dict)


if __name__ == "__main__":
    with StudyBot("!") as bot:
        bot.run(get_tokens()[0])
