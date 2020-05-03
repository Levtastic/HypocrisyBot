from ..user_level import UserLevel
from ..commands import CommandException


class UserCommands:
    def __init__(self, bot):
        self.bot = bot
        self.user_level = UserLevel.server_owner

        self.register()

    def register(self):
        shared_info = (
            'usertype can be "admin" or "blacklist"\n'
            '\n'
            'Admins are able to give server-level commands to the bot'
            ' without needing the Manage Channel permission in the server'
            ' or any channels.\n'
            '\n'
            'Blacklisted users are completely ignored by the bot in your'
            ' server, even if they do have the Manage Channel permission.'
            ' (Note: The server owner cannot be blacklisted)\n'
            '\n'
            'If a user is both an admin and blacklisted using this command,'
            ' the bot will treat them as Blacklisted'
        )

        self.bot.commands.register_handler(
            'add user',
            self.cmd_add_user,
            user_level=self.user_level,
            description=(
                'Adds either an admin or a blacklisted user to a server\n'
                '\n' + shared_info
            )
        )
        self.bot.commands.register_handler(
            'remove user',
            self.cmd_remove_user,
            user_level=self.user_level,
            description=(
                'Removes either an admin or a blacklisted user from a server\n'
                '\n' + shared_info
            )
        )
        self.bot.commands.register_handler(
            'list users',
            self.cmd_list_users,
            user_level=self.user_level,
            description=(
                'Lists users with admin or blacklisted status given through'
                ' the `add user` command.\n'
                'If you leave out the server name parameter, the bot will'
                ' reply with **ALL** users you have permission to view in all'
                ' servers where you are considered an admin by the bot.\n'
                'To only view users for a specific server, name the server or'
                ' use the keyword "here" in the `server name` parameter'
                ' slot.\n'
                '\n' + shared_info
            )
        )

    async def cmd_add_user(self, message, username, usertype,
                           guildname='here'):
        guild = self.get_guild(guildname, message)
        duser = self.get_discord_user(guild, username)
        user = self.ensure_user(guild, duser)
        userguild = self.ensure_userguild(guild, user)

        if usertype == 'admin':
            userguild.admin = True
            userguild.save()

            return await self.bot.send_message(
                message.channel,
                'Admin `{!s}` added to `{}` successfully'.format(
                    duser,
                    guild.name
                )
            )

        elif usertype == 'blacklist':
            userguild.blacklisted = True
            userguild.save()

            return await self.bot.send_message(
                message.channel,
                'Blacklist `{!s}` added to `{}` successfully'.format(
                    duser,
                    guild.name
                )
            )

        raise CommandException('Unknown user type `{}`'.format(usertype))

    def get_guild(self, name, message):
        if name.lower() == 'here':
            if message.channel.is_private:
                raise CommandException(
                    "This command isn't supported for private channels"
                )

            return message.guild

        guild = self.bot.get_guild(name)
        if guild:
            return guild

        gen = self.get_guilds_with_permission(name, message.author)
        guild = next(gen, None)

        if guild:
            return guild

        raise CommandException('Server `{}` not found'.format(name))

    def get_guilds_with_permission(self, name, member):
        for guild in self.bot.guilds:
            if UserLevel.get(member, guild) < self.user_level:
                continue

            if name in guild.name:
                yield guild

    def ensure_user(self, guild, duser):
        user = self.bot.database.get_User_by_user_did(duser.id)

        if not user:
            user = self.bot.database.get_User()
            user.user_did = duser.id
            user.save()

        return user

    def get_discord_user(self, guild, name):
        if name[0:3] == '<@!':
            retmember = guild.get_member(name[3:-1])

        elif name[0:2] == '<@':
            retmember = guild.get_member(name[2:-1])

        else:
            name = name.lower()

            for member in guild.members:
                if name in str(member).lower():
                    retmember = member

        if retmember:
            return retmember

        raise CommandException('User `{}` not found'.format(name))

    def ensure_userguild(self, guild, user):
        userguild = self.bot.database.get_UserGuild()
        userguild = userguild.get_by(
            guild_did=guild.id,
            user_id=user.id
        )

        if not userguild:
            userguild = self.bot.database.get_UserGuild()
            userguild.guild_did = guild.id
            userguild.user_id = user.id
            userguild.save()

        return userguild

    async def cmd_remove_user(self, message, username, usertype,
                              guildname='here'):
        guild = self.get_guild(guildname, message)
        duser = self.get_discord_user(guild, username)
        user = self.ensure_user(guild, duser)
        userguild = self.ensure_userguild(guild, user)

        if usertype == 'admin':
            userguild.admin = False
            userguild.save()

            self.clean_up(user, userguild)

            return await self.bot.send_message(
                message.channel,
                'Admin `{!s}` removed from `{}` successfully'.format(
                    duser,
                    guild.name
                )
            )

        elif usertype == 'blacklist':
            userguild.blacklisted = False
            userguild.save()

            self.clean_up(user, userguild)

            return await self.bot.send_message(
                message.channel,
                'Blacklist `{!s}` removed from `{}` successfully'.format(
                    duser,
                    guild.name
                )
            )

        raise CommandException('Unknown user type `{}`'.format(usertype))

    def clean_up(self, user, userguild):
        if not userguild.admin and not userguild.blacklisted:
            userguild.delete()

        if not user.user_guilds:
            user.delete()

    async def cmd_list_users(self, message, listtype='both', guildname='',
                             username=''):
        users = self.bot.database.get_User_list()

        if guildname:
            guild = self.get_guild(guildname, message)
        else:
            guild = None

        text = await self.get_list_text(users, username, listtype, guild,
                                        message)

        await self.bot.send_message(message.channel, text)

    async def get_list_text(self, users, username, listtype, guild, message):
        pieces = []

        for user in users:
            for userguild in user.user_guilds:
                if not self.check_listtype(userguild, listtype):
                    continue

                if not self.check_guild(userguild, guild, message.author):
                    continue

                if not await self.check_username(user, username):
                    continue

                pieces.append(
                    await self.get_list_text_piece(user, userguild, guild)
                )

        if not pieces:
            return 'No `users` found.'

        return '\u200C\n{}'.format('\n'.join(pieces))

    def check_listtype(self, userguild, listtype):
        if listtype == 'admin':
            return userguild.admin

        if listtype == 'blacklist':
            return userguild.blacklisted

        if listtype in ('', 'both'):
            return True

        raise CommandException('Unrecognised list type `{}`'.format(listtype))

    def check_guild(self, userguild, guild, member):
        if guild and guild.id != userguild.guild_did:
            return False

        return UserLevel.get(member, userguild.guild) >= self.user_level

    async def check_username(self, user, username):
        return username in str(await user.get_user())

    async def get_list_text_piece(self, user, userguild, guild):
        piece = '`{!s}`'.format(await user.get_user())

        if userguild.admin:
            piece += ' `admin`'

        if userguild.blacklisted:
            piece += ' `blacklisted`'

        if not guild:  # user didn't specify a guild
            piece = '`{0.guild.name}` {1}'.format(userguild, piece)

        return piece
