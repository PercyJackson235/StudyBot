#!/home/user/dev/StudyBot/venv/bin/python3
from discord.ext import commands
from discord import Status
import sqlite3
import asyncio
from contextlib import closing
from datetime import datetime


bot = commands.Bot(command_prefix = '!')
admin_role_id = 814693343236980786
command_list = []
# This dict is referred to for getting the descriptions of commands for the !help command.
help_dict = {'add-time': 'Add the personal amount of study time in minutes.',
             'get-time': 'Retrieves the personal amount of hours studied.',
             'all-time': 'Retrieves the total amount of study time.',
             'shutdown': 'Shuts down the Bot. Need bot-admin.',
             'start-timer': 'Starts study timer.',
             'stop-timer': 'Stops study timer.',
             'verify-study': 'Verify the amount of study time: true or false.'}
lock = asyncio.Lock()


def get_token():
    """Loads environment variables from dotenv files, and returns the value of the discord token.
    :return: String from DISCORD_TOKEN key in .env file"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return(os.getenv('DISCORD_TOKEN'))



def setup_database():
    """Create the database table if it doesn't exist.
    :return: Nothing"""
    global db_conn 
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


def log_writer(err: Exception, filename: str = 'error.log'):
    with open(filename, 'a') as f:
        f.write("{}\n".format(repr(err)))


class AltHelp(commands.DefaultHelpCommand):
    async def send_pages(self):
        await super().send_pages()

@bot.event
async def on_ready():
    msg = '{} is online.'.format(bot.user)
    channel = bot.get_channel(816133808533012512)
    await channel.send(msg)


setup_database()
if __name__ == '__main__':
    cogs = ['admin_cog', 'time_tracker_cog', 'timer_cog']
    for i in cogs:
        bot.load_extension(i)
    bot.run(get_token())

    # Finish database stuff after the bot client disconnects.
    db_conn.commit()
    db_conn.close()



