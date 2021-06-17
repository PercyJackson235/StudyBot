import discord
from discord.ext import commands
from contextlib import closing
from typing import Union
import studybot

class Time_Tracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    

    @commands.command(name="add-time", help=studybot.help_dict.get('add-time'))
    async def add_time(self, ctx, minutes: Union[int, str] = 0):
        if isinstance(minutes, str):
            if not minutes.isdigit():
                await ctx.reply("'{}' is not a proper value".format(minutes))
                return
            minutes = int(minutes)
        if minutes < 0:
            await ctx.reply("'{}' is not a proper value".format(minutes))
            return
        msg = "Added {} hours and {} minutes."
        username = str(ctx.author)
        with closing(studybot.db_conn.cursor()) as conn:
            async with studybot.lock:
                query = 'SELECT minutes FROM study_time WHERE name = ? AND server = ?'  # noqa: E501
                conn.execute(query, (username, str(ctx.guild)))
                if conn.fetchone() is None:
                    query = 'INSERT INTO study_time (name, minutes, server)'
                    query += ' VALUES (?, ?, ?)'
                    conn.execute(query, (username, 0, str(ctx.guild)))
                query = 'UPDATE study_time SET minutes = minutes + ? '
                query += 'WHERE name = ? AND server = ?'
                conn.execute(query, (minutes, username, str(ctx.guild)))
                studybot.db_conn.commit()
        try:
            await ctx.reply(msg.format(*divmod(minutes, 60)))  # noqa: E501
        except Exception as e:
            log_writer(e)


    @commands.command(name="get-time", help=studybot.help_dict.get('get-time'))
    async def get_time(self, ctx):
        username = str(ctx.author)
        with closing(studybot.db_conn.cursor()) as conn:
            async with studybot.lock:
                query = 'SELECT minutes FROM study_time WHERE name = ? AND server = ?'  # noqa: E501
                conn.execute(query, (username, str(ctx.guild)))
                value = conn.fetchone()
                if value is None:
                    query = 'INSERT INTO study_time (name, minutes, server) '
                    query += 'VALUES (?, ?, ?)'
                    conn.execute(query, (username, 0, str(ctx.guild)))
                    query = 'SELECT minutes FROM study_time WHERE name = ? AND server = ?'  # noqa: E501
                    conn.execute(query, (username, str(ctx.guild)))
                    value = conn.fetchone()[0]
                else:
                    value = value[0]
                msg = "You have contributed {} hours and {} minutes to total."
                await ctx.reply(msg.format(*divmod(value, 60)))
                studybot.db_conn.commit()


    @commands.command(name="all-time", help=studybot.help_dict.get('all-time'))
    async def all_time(self, ctx):
        with closing(studybot.db_conn.cursor()) as conn:
            async with studybot.lock:
                query = 'SELECT minutes FROM study_time WHERE server = ?'
                conn.execute(query, (str(ctx.guild),))
                value = sum(i[0] for i in conn.fetchall())
                msg = "The total amount of time studying is {} hours"
                msg += " and {} minutes."
                await ctx.reply(msg.format(*divmod(value, 60)))
                studybot.db_conn.commit()


def setup(bot):
    bot.add_cog(Time_Tracking(bot))