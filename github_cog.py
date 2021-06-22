import discord
from discord.ext import commands
from github import Github
import closing
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
            # Get the Organization object and the user object.
            g_user = g.get_user(github_name)
            g_org = g.get_organization(studybot.TOKENS.get('GITHUB_ORG_NAME'))

            # Verify that the user has not already invited a GitHub account to the org.
            with closing(studybot.db_conn.cursor()) as conn:
                async with studybot.lock:
                    query = 'SELECT github_id FROM github_invites WHERE discord_id = ?'  # noqa: E501
                    conn.execute(query, ctx.author.id)
                    value = conn.fetchone()
                    if value is None:
                        # Invite the user to the organization.
                        g_org.invite_user(g_user)
                        # Add the Discord ID and the GitHub ID to the database table
                        query = 'INSERT INTO study_time (discord_id, github_id) VALUES (?, ?)'
                        conn.execute(query, (ctx.author.id, g_user.id))
                        # Send a confirmation message in Discord.
                        ctx.message.reply(f'Invited {g_user.name} to the GitHub Organization.')
                    else:
                        msg = f'Cannot invite {g_user.name} to the organization, because you have already invited '
                        msg += 'another GitHub account. Please contact a moderator if this is a mistake.'
                        ctx.message.reply(msg)
                    studybot.db_conn.commit()


def setup(bot):
    bot.add_cog(GitHub_Integration(bot))
