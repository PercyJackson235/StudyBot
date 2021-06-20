#!/home/user/dev/StudyBot/venv/bin/python3
from discord import Intents
from discord.ext import commands
import sqlite3
import asyncio
from contextlib import closing
from typing import Dict


intents = Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)
# This dict is referred to for getting the
# descriptions of commands for the !help command.
help_dict = {'add-time': 'Add the personal amount of study time in minutes.',
             'get-time': 'Retrieves the personal amount of hours studied.',
             'all-time': 'Retrieves the total amount of study time.',
             'shutdown': 'Shuts down the Bot. Need bot-admin.',
             'start-timer': 'Starts study timer.',
             'stop-timer': 'Stops study timer.',
             'verify-study': 'Verify the amount of study time: true or false.'}
lock = asyncio.Lock()


def get_tokens() -> Dict[str, str]:
    """Loads environment variables from dotenv files, and returns the value of the discord token.
    \n:return: Dictionary from DISCORD_TOKEN, ADMIN_ROLE_ID, and CHANNEL_ID key in .env file"""  # noqa: E501
    import os
    from dotenv import load_dotenv
    load_dotenv()
    env_keys = ("DISCORD_TOKEN", "ADMIN_ROLE_ID", "CHANNEL_ID")
    return {key: os.getenv(key) for key in env_keys}


TOKENS = get_tokens()
admin_role_id = int(TOKENS.get("ADMIN_ROLE_ID"))


def setup_database() -> sqlite3.Connection:
    """Create the database table if it doesn't exist.
    Also defines db_conn global variable for connecting to the db.
    :return: sqlite3.Connection"""
    db_conn = sqlite3.connect('server.db')
    with closing(db_conn.cursor()) as conn:
        table = 'CREATE TABLE IF NOT EXISTS study_time '
        table += '(name text, minutes integer, server text)'
        conn.execute(table)
        db_conn.commit()
        table = 'CREATE TABLE IF NOT EXISTS live_timer '
        table += '(name text, server text, timestamp real)'
        db_conn.execute(table)
        db_conn.commit()
    return db_conn


def log_writer(err: Exception, filename: str = 'error.log'):
    """Writes to the log file 'error.log'
    :return: None"""
    with open(filename, 'a') as f:
        f.write("{}\n".format(repr(err)))


@bot.event
async def on_ready():
    msg = '{} is online.'.format(bot.user)
    channel = bot.get_channel(int(TOKENS.get("CHANNEL_ID")))
    await channel.send(msg)


db_conn = setup_database()

if __name__ == '__main__':
    # Imports the cogs so the bot knows they exist.
    cogs = {'admin_cog', 'time_tracker_cog', 'timer_cog'}
    for i in cogs:
        bot.load_extension(i)
    # Starts the bot.
    # Note: This blocks until the bot shuts down.
    bot.run(TOKENS.get("DISCORD_TOKEN"))

    # Finish database stuff after the bot client disconnects.
    db_conn.commit()
    db_conn.close()
