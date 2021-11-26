from discord.ext import commands
from discord.ext.commands import UserNotFound, UserConverter
from github import Github
import github
from contextlib import closing
import studybot
from typing import Union
from datetime import datetime, timezone, timedelta


EST = timezone(timedelta(hours=-4), 'EST')


async def check_prev_inv(discord_user) -> Union[int, None]:
    """
    Checks the database to see if/who a specific discord user has invited to the github organization.
    :param discord_user: discord.User object.
    :return: tuple containing the id of the github account the user invited, or None.
    """
    with closing(studybot.db_conn.cursor()) as conn:
        async with studybot.lock:
            query = 'SELECT github_id FROM github_invites WHERE discord_id = ?'
            conn.execute(query, (discord_user.id,))
            return conn.fetchone()


class GitHubIntegration(commands.Cog, name='GitHub Integration'):
    def __init__(self, bot):
        self.bot = bot
        self.user_converter = UserConverter()

    @commands.command(name='github-join', help=studybot.help_dict.get('github-join'))
    async def join(self, ctx: commands.Context, github_name: str = None) -> None:
        # Make sure they included the github_name arg, and send a response.
        if not github_name:
            msg = 'You need to include your GitHub Username like this: '
            msg += '`!github-join StudyBot`'
            await ctx.reply(msg)
            return
        else:
            github_session = Github(studybot.TOKENS.get('GITHUB_API_KEY'))
            # Get the user object.
            try:
                github_user = github_session.get_user(github_name)
            except github.UnknownObjectException:
                msg = 'The GitHub user you requested cannot be found. Double-Check '
                msg += 'your spelling.'
                await ctx.reply(msg)
                return
            # Get the organization object.
            try:
                placement_org = github_session.get_organization(studybot.github_org_name)  # noqa: E501
            except github.UnknownObjextException:
                msg = 'The GitHub organization you are trying to join cannot be '
                msg += 'found. Please try again later, and contact a mod if the '
                msg += 'issue persists.'
                await ctx.reply(msg)
                return

            # Verify that the user has not already invited a GitHub account to the org.  # noqa: E501
        if await check_prev_inv(ctx.author) is None:
            # Verify that the user is not already in the org.
            if placement_org.has_in_members(github_user):
                await ctx.reply('That user is already in the organization, and cannot be invited.')  # noqa: E501
                return
            # Invite the user to the organization.
            else:
                placement_org.invite_user(github_user)

            # Add the Discord ID and the GitHub ID to the database table
            with closing(studybot.db_conn.cursor()) as conn:
                async with studybot.lock:
                    query = 'INSERT INTO github_invites (discord_id, github_id) VALUES (?, ?)'  # noqa: E501
                    conn.execute(query, (ctx.author.id, github_user.id))
                    studybot.db_conn.commit()

            # Send a confirmation message in Discord.
            due_date = datetime.now(tz=EST) + timedelta(weeks=1)
            due_date = due_date.strftime("%B %d, %Y %Z")
            msg = f"Invited {github_user.login} to the GitHub Organization. Please"
            msg += " accept the invitation link - "
            msg += "https://github.com/orgs/Python-Practice-Discord/invitation - "
            msg += f"before {due_date} or the invitation will expire."
            await ctx.reply(msg)
        else:
            msg = f"Cannot invite {github_user.login} to the organization, because "
            msg += "you have already invited another GitHub account. Please contact"
            msg += " a moderator if this is a mistake."
            await ctx.reply(msg)

    @commands.command(name='github-reset', help=studybot.help_dict.get('github-reset'))  # noqa: E501
    @commands.has_role(studybot.admin_role_id)
    async def reset_user(self, ctx: commands.Context, discord_user: str = None) -> None:  # noqa: E501
        try:
            if discord_user is None:
                await ctx.reply('You need to tag the user to reset their abilities.')
                return
            discord_user = await self.user_converter.convert(ctx, discord_user)
        except UserNotFound:
            await ctx.reply(f"{discord_user!r} is not a valid discord user.")
            return

        # Find who the user previously invited to the org.
        db_output = await check_prev_inv(discord_user)
        # If the user hasn't invited anyone
        if db_output is None:
            await ctx.reply('This user has not invited anyone to the org.')
            return

        g = Github(studybot.TOKENS.get('GITHUB_API_KEY'))
        # Get the GitHub user object.
        try:
            g_user = g.get_user_by_id(int(db_output[0]))
        except github.UnknownObjextException:
            g_user = None
        # Get the GitHub organization object.
        try:
            g_org = g.get_organization(studybot.github_org_name)
        except github.UnknownObjectException:
            msg = 'The GitHub organization cannot be found. Please try again later.'
            await ctx.reply(msg)
            return

        # Revoke the GitHub account's invite or remove them from the Organization (if the user exists).  # noqa: E501
        try:
            if g_user:
                g_org.remove_from_membership(g_user)
        except github.GithubException:
            from traceback import print_exc
            msg = studybot.StrFile(f"Github User {g_user.login} isn't a part of the Org.\n")  # noqa: E501
            print_exc(file=msg)
            studybot.error_logger.error(msg)
            # bot-admin id = 814693343236980786
            ctx.send("<@&814693343236980786> Check studybot, there may be an error.")

        # Delete the Database entry showing that the user invited someone
        with closing(studybot.db_conn.cursor()) as conn:
            async with studybot.lock:
                query = 'DELETE FROM github_invites WHERE discord_id = ?'
                conn.execute(query, (discord_user.id, ))
                studybot.db_conn.commit()
        await ctx.reply(f'Successfully reset {discord_user.mention}s ability to invite users')  # noqa: E501


def setup(bot):
    bot.add_cog(GitHubIntegration(bot))
