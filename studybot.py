#!/home/user/dev/StudyBot/venv/bin/python3
from discord import Intents
from discord.ext import commands
import sqlite3
import asyncio
from contextlib import closing
from typing import Dict
import logging


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
             'verify-study': 'Verify the amount of study time: true or false.',
             'github-join': 'Invites your GitHub account to our GitHub organization.',  # noqa: E501
             'github-reset': 'Allows a blocked user to invite an account it the org. Tag the user. Need bot-admin.'}  # noqa: E501
lock = asyncio.Lock()


def get_tokens() -> Dict[str, str]:
    """Loads environment variables from dotenv files, and returns the value of the discord token.
    \n:return: Dictionary containing DISCORD_TOKEN, ADMIN_ROLE_ID, CHANNEL_ID, GITHUB ORG_NAME,
     and GITHUB_API_KEY from .env file"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    env_keys = ("DISCORD_TOKEN", "ADMIN_ROLE_ID", "CHANNEL_ID",
                "GITHUB_ORG_NAME", "GITHUB_API_KEY")
    return {key: os.getenv(key) for key in env_keys}


TOKENS = get_tokens()
admin_role_id = int(TOKENS.get("ADMIN_ROLE_ID"))
github_org_name = TOKENS.get("GITHUB_ORG_NAME")


def setup_database() -> sqlite3.Connection:
    """Create the database table if it doesn't exist.
    Also defines db_conn global variable for connecting to the db.
    :return: sqlite3.Connection"""
    db_conn = sqlite3.connect('server.db')
    with closing(db_conn.cursor()) as conn:
        # Create study_time database table.
        table = 'CREATE TABLE IF NOT EXISTS study_time '
        table += '(id integer, minutes integer, server text)'
        conn.execute(table)
        db_conn.commit()
        # Create live_timer database table.
        table = 'CREATE TABLE IF NOT EXISTS live_timer '
        table += '(id integer, server text, timestamp real)'
        db_conn.execute(table)
        db_conn.commit()
        # Create github_invites database table.
        table = 'CREATE TABLE IF NOT EXISTS github_invites'
        table += '(discord_id integer, github_id integer)'
        db_conn.execute(table)
        db_conn.commit()
    return db_conn


def log_creater(filename: str = 'error.log') -> logging.Logger:
    """Creates a logger for studybot that writes to file 'error.log'
    :return: logging.Logger"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename)
    fmt = logging.Formatter("{name}:{levelname} -> {asctime} - {message}", style='{')
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


class StrFile(object):
    def __init__(self, text: str = ''):
        self._text = text

    def write(self, text: str = '') -> None:
        self._text += text

    def __repr__(self) -> str:
        return self._text


@bot.event
async def on_ready() -> None:
    msg = '{} is online.'.format(bot.user)
    channel = bot.get_channel(int(TOKENS.get("CHANNEL_ID")))
    await channel.send(msg)


db_conn = setup_database()
error_logger = log_creater()


if __name__ == '__main__':
    # Imports the cogs so the bot knows they exist.
    cogs = {'admin_cog', 'time_tracker_cog', 'timer_cog', 'github_cog'}
    for i in cogs:
        bot.load_extension(i)
    # Starts the bot.
    # Note: This blocks until the bot shuts down.
    bot.run(TOKENS.get("DISCORD_TOKEN"))

    # Finish database stuff after the bot client disconnects.
    db_conn.commit()
    db_conn.close()
