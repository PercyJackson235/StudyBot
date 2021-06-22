from discord.ext import commands
import studybot
from datetime import datetime
from contextlib import closing


class Study_Timer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='start-timer', help=studybot.help_dict.get('start-timer'))
    async def start_study(self, ctx):
        timestamp = datetime.now().timestamp()
        userid, server = ctx.author.id, str(ctx.guild)
        with closing(studybot.db_conn.cursor()) as conn:
            async with studybot.lock:
                query = 'SELECT timestamp FROM live_timer WHERE id = ? AND server = ?'  # noqa: E501
                conn.execute(query, (userid, server))
                result = conn.fetchone()
                if result is None:
                    query = 'INSERT INTO live_timer (id, server, timestamp) '
                    query += 'VALUES (?, ?, ?)'
                    conn.execute(query, (userid, server, timestamp))
                elif result[0] == 0.0:
                    query = 'UPDATE live_timer SET timestamp = ? '
                    query += 'WHERE id = ? AND server = ?'
                    conn.execute(query, (timestamp, userid, server))
                elif bool(result[0]):
                    await ctx.reply('Already started timer.', delete_after=120)
                    studybot.db_conn.commit()
                    return
                else:
                    await ctx.reply('Sorry. Unexpected Error happend.')
                    err = 'In start_study, result is not None, 0.0, or timestamp.'
                    err += f'user = {str(ctx.author)}, userid = {userid}, '
                    err += f'Server = {server}, timestamp = {timestamp}.'
                    studybot.log_writer(err)
                    studybot.db_conn.commit()
                    return
        await ctx.reply('Okay. Started Timer.', delete_after=120)
        studybot.db_conn.commit()

    @commands.command(name='stop-timer', help=studybot.help_dict.get('stop-timer'))
    async def stop_study(self, ctx):
        userid, server = ctx.author.id, str(ctx.guild)
        result = 0.0
        minutes = 0
        with closing(studybot.db_conn.cursor()) as conn:
            async with studybot.lock:
                query = 'SELECT timestamp FROM live_timer WHERE id = ? '
                query += 'AND server = ?'
                conn.execute(query, (userid, server))
                result = conn.fetchone()
                if result is None:
                    await ctx.reply('Never started timer.', delete_after=120)
                    studybot.db_conn.commit()
                    return
                elif result[0] == 0.0:
                    await ctx.reply('Never started timer.', delete_after=120)
                    studybot.db_conn.commit()
                    return
                elif bool(result[0]):
                    result = datetime.now() - datetime.fromtimestamp(result[0])
                    minutes, seconds = divmod(result.seconds, 60)
                    minutes += round(seconds / 60)
                    query = 'UPDATE live_timer SET timestamp = ? '
                    query += 'WHERE id = ? AND server = ?'
                    conn.execute(query, (float(minutes), userid, server))
                else:
                    await ctx.reply('Sorry. Unexpected Error happend.')
                    err = 'In stop_study, result is not None, 0.0, or timestamp.'
                    err += f'user = {str(ctx.author)}, userid = {userid} ,'
                    err += f'and Server = {server}'
                    studybot.log_writer(err)
                    studybot.db_conn.commit()
                    return
        msg = 'Timer is stopped. Please "!verify-study" if {} minutes is'
        msg += ' the proper amount of study time. If false please "!verify-'
        msg += 'study False".'
        await ctx.reply(msg.format(minutes), delete_after=300)
        studybot.db_conn.commit()

    @commands.command(name='verify-study', help=studybot.help_dict.get('verify-study'))  # noqa: E501
    async def verify(self, ctx, value: bool = True):
        userid, server = ctx.author.id, str(ctx.guild)
        msg = 'Added {} hours and {} minutes.'
        minutes = 0
        with closing(studybot.db_conn.cursor()) as conn:
            async with studybot.lock:
                if value:
                    query = 'SELECT timestamp FROM live_timer WHERE id = ? '
                    query += 'AND server = ?'
                    conn.execute(query, (userid, server))
                    result = conn.fetchone()
                    if result[0] is None:
                        errormsg = 'Timer was never set. Cannot verify.'
                        await ctx.reply(errormsg, delete_after=60)
                        studybot.db_conn.commit()
                        return
                    elif result[0] == 0.0:
                        errormsg = 'Timer was never set. Cannot verify.'
                        await ctx.reply(errormsg, delete_after=60)
                        studybot.db_conn.commit()
                        return
                    elif bool(result[0]):
                        if divmod(result[0], 1)[1] != 0.0:
                            msg = 'Timer was never stopped. Cannot verify.'
                            await ctx.reply(msg)
                            studybot.db_conn.commit()
                            return
                        result = minutes = int(result[0])
                        query = 'UPDATE study_time SET minutes = minutes + ? '
                        query += 'WHERE id = ? AND server = ?'
                        conn.execute(query, (result, userid, server))
                        query = 'UPDATE live_timer SET timestamp = ? '
                        query += 'WHERE id = ? AND server = ?'
                        conn.execute(query, (0.0, userid, server))
                    else:
                        await ctx.reply('Sorry. Unexpected Error happend.')
                        msg = f'verify_study. userid = {userid} and '
                        msg += f'user = {str(ctx.author)}, Server = {server}'
                        studybot.log_writer(msg)
                        studybot.db_conn.commit()
                        return
                else:
                    msg = 'Okay. Discarding recorded study time.'
                    await ctx.reply(msg, delete_after=30)
                    query = 'UPDATE live_timer SET timestamp = ? '
                    query += 'WHERE id = ? AND server = ?'
                    conn.execute(query, (0.0, userid, server))
                    return
        studybot.db_conn.commit()
        await ctx.reply(msg.format(*divmod(minutes, 60)))


def setup(bot):
    bot.add_cog(Study_Timer(bot))
