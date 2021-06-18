import discord
from discord.ext import commands
from github import Github
import studybot

class GitHub_Integration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    

    @commands.command(name='github-join', help=studybot.help_dict.get('github-join'))
    async def join(self, ctx, github_name = 'null'):
        # Make sure they included the github_name arg, and send a response.
        if github_name == 'null':
            msg = ('You need to include your GitHub Username like this: ')
            msg += ('`!github-join StudyBot`')
            await ctx.message.reply(msg)
            return
        else:
            g = Github(studybot.TOKENS.get('GITHUB_API_KEY'))
            # Get the Organization object and the user object.
            g_user = g.get_user(github_name)
            g_org = g.get_organization('Python-Practice-Discord')
            # Invite the user to the organization.
            g_org.invite_user(g_user)
            ctx.message.reply(f'Invited {g_user.name} to the Python-Practice-Discord GitHub Organization.')


def setup(bot):
    bot.add_cog(GitHub_Integration(bot))