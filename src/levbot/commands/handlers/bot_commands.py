import discord
import logging

from collections import defaultdict
from datetime import datetime
from discord import NotFound, Forbidden, File
from ...user_level import UserLevel


class BotCommands:
    def __init__(self, commands):
        self.bot = commands.bot
        self.register(commands)

    def register(self, commands):
        commands.register_handler(
            'list all channels',
            self.cmd_list_all_channels,
            user_level=UserLevel.global_bot_admin
        )
        commands.register_handler(
            'list all users',
            self.cmd_list_all_users,
            user_level=UserLevel.global_bot_admin
        )
        commands.register_handler(
            'quit',
            self.cmd_quit,
            user_level=UserLevel.bot_owner
        )
        commands.register_handler(
            'restart',
            self.cmd_restart,
            user_level=UserLevel.bot_owner
        )
        commands.register_handler(
            'say',
            self.cmd_say,
            user_level=UserLevel.guild_bot_admin
        )
        commands.register_handler(
            'sayd',
            self.cmd_sayd,
            user_level=UserLevel.guild_bot_admin
        )
        commands.register_handler(
            'backup',
            self.cmd_backup,
            user_level=UserLevel.guild_bot_admin
        )

        if self.bot.main_settings.offer_invite_link:
            commands.register_handler(
                'invite',
                self.cmd_invite,
                user_level=UserLevel.user
            )
        if self.bot.main_settings.source_url:
            commands.register_handler(
                'source',
                self.cmd_source,
                user_level=UserLevel.user
            )

        if self.bot.main_settings.donate_url:
            commands.register_handler(
                'donate',
                self.cmd_donate,
                user_level=UserLevel.user
            )

    async def cmd_list_all_channels(self, message, channel_filter=''):
        """Lists channels the bot can currently see"""

        channels = defaultdict(list)

        for guild, channel in self.get_text_channels(channel_filter):
            channels[guild].append(channel)

        await message.channel.send(
            self.get_channels_text(channels)
        )

    def get_text_channels(self, channel_filter):
        for guild in self.bot.guilds:
            for channel in guild.channels:
                if channel.type != discord.ChannelType.text:
                    continue

                if channel_filter.lower() not in channel.name.lower():
                    continue

                yield guild, channel

    def get_channels_text(self, channels):
        if not channels:
            return 'No channels found'

        return '\u200C\n{}'.format('\n'.join(
            self.get_channels_text_pieces(channels))
        )

    def get_channels_text_pieces(self, channels):
        for guild in channels.keys():
            yield 'Server: `{}`'.format(guild)

            for channel in channels[guild]:
                channel_text = '    `{0.id}`: `{0.name}`'.format(channel)

                if not channel.permissions_for(guild.me).send_messages:
                    channel_text += ' (cannot message)'

                yield channel_text

    async def cmd_list_all_users(self, message, user_filter=''):
        """Lists users the bot can currently see"""

        members = defaultdict(list)

        for guild, member in self.get_members(user_filter):
            members[guild].append(member)

        await message.channel.send(
            self.get_users_text(members)
        )

    def get_members(self, user_filter):
        for guild in self.bot.guilds:
            for member in guild.members:
                if user_filter.lower() not in member.name.lower():
                    continue

                yield guild, member

    def get_users_text(self, members):
        if not members:
            return 'No users found'

        return '\u200C\n{}'.format('\n'.join(
            self.get_users_text_pieces(members))
        )

    def get_users_text_pieces(self, members):
        for guild in members.keys():
            yield 'Server: `{}`'.format(guild)

            for member in members[guild]:
                member_text = '    `{0.id}`: `{0.name}`'.format(member)

                if member.nick:
                    member_text += ' `({0.nick})`'.format(member)

                if member.bot:
                    member_text += ' `BOT`'

                yield member_text

    async def cmd_invite(self, message):
        """Sends a link in a PM for inviting the bot to your server"""

        await message.author.send(
            'Use this invite link to add me to your server: {}'.format(
                discord.utils.oauth_url(self.bot.user.id)
            )
        )

    async def cmd_quit(self, message):
        """Immediately shuts down the bot"""

        logging.info(f'Shutdown command received from {message.author}')
        await message.channel.send('Shutting down.')
        await self.bot.logout()

    async def cmd_restart(self, message):
        """Immediately shuts down and restarts the bot"""

        logging.info(f'Restart command received from {message.author}')
        await message.channel.send('Restarting.')
        await self.bot.restart()

    async def cmd_say(self, message, text):
        """Sends a message in the location the command is given.

            The message is everything following the command."""

        await message.channel.send(text)

    async def cmd_sayd(self, message, text):
        """Replaces the command with the given message.

            This is achieved by deleting the message containing the command.
            The "given message" is everything following the command.

            This command does nothing if the bot can't delete messages"""

        try:
            await message.delete()
            await self.cmd_say(message, text)

        except (NotFound, Forbidden):
            pass

    async def cmd_backup(self, message):
        """Sends a snapshot of the database in a PM.

            Snapshots are attached as .db files and are created when requested.
            The bot will also reply with the current timestamp."""

        await message.author.send(
            'BACKUP ' + datetime.now().isoformat(' '),
            file=File(self.bot.main_settings.db_name)
        )

    async def cmd_source(self, message):
        """Sends a link in a PM to view the bot source code."""

        await message.author.send(self.bot.main_settings.source_url)

    async def cmd_donate(self, message):
        """Sends a link in a PM for donating to the bot creator."""

        await message.author.send(
            self.bot.main_settings.donate_url + (
                '\n\n'
                "Donating isn't required to use me, but any money you want to"
                ' send will be very much appreciated by my dad who spent many'
                ' months to make me, and who still has to jump in and help me'
                ' when I get confused.'
            )
        )
