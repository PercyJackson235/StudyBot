import discord
from discord.ext import commands
from github import Github
from contextlib import closing
import studybot


class GitHub_Integration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='github-join', help=studybot.help_dict.get('github-join'))
    async def join(self, ctx, github_name='null'):
        # Make sure they included the github_name arg, and send a response.
        if github_name == 'null':
            msg = 'You need to include your GitHub Username like this: '
            msg += '`!github-join StudyBot`'
            await ctx.message.reply(msg)
            return
        else:
            g = Github(studybot.TOKENS.get('GITHUB_API_KEY'))
            # Get the user object.
            try:
                g_user = g.get_user(github_name)
            except:
                await ctx.message.reply('The GitHub user you requested cannot be found. Double-Check your spelling.')
                return()
            # Get the organization object.
            try:
                g_org = g.get_organization(studybot.TOKENS.get('GITHUB_ORG_NAME'))
            except:
                msg = 'The GitHub organization cannot be found. Please try again later, '
                msg += 'or contact a mod if the issue persists.'
                await ctx.message.reply(msg)
                return()

            # Verify that the user has not already invited a GitHub account to the org.
            with closing(studybot.db_conn.cursor()) as conn:
                async with studybot.lock:
                    query = 'SELECT github_id FROM github_invites WHERE discord_id = ?'
                    conn.execute(query, (ctx.author.id, ))
                    value = conn.fetchone()
                    if value is None:
                        # Invite the user to the organization.
                        g_org.invite_user(g_user)
                        # Add the Discord ID and the GitHub ID to the database table
                        query = 'INSERT INTO github_invites (discord_id, github_id) VALUES (?, ?)'
                        conn.execute(query, (ctx.author.id, g_user.id))
                        # Send a confirmation message in Discord.
                        await ctx.message.reply(f'Invited {g_user.name} to the GitHub Organization.')
                    else:
                        msg = f'Cannot invite {g_user.login} to the organization, because you have already invited '
                        msg += 'another GitHub account. Please contact a moderator if this is a mistake.'
                        await ctx.message.reply(msg)
                    studybot.db_conn.commit()


def setup(bot):
    bot.add_cog(GitHub_Integration(bot))
