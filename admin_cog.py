from discord import Status
from discord.ext import commands
import studybot
from typing import Union
import asyncio

class Admin_Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(help=studybot.help_dict.get('shutdown'))
    @commands.has_role(studybot.admin_role_id)
    async def shutdown(self, ctx):
        text = 'Okay. I, {}, am shutting down'
        await self.bot.change_presence(status=Status.offline)
        await ctx.reply(text.format(self.bot.user))
        await asyncio.sleep(10)
        await self.bot.close()
        return

def setup(bot):
    bot.add_cog(Admin_Commands(bot))