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
                           servername='here'):
        server = self.get_server(servername, message)
        duser = self.get_discord_user(server, username)
        user = self.ensure_user(server, duser)
        userserver = self.ensure_userserver(server, user)

        if usertype == 'admin':
            userserver.admin = True
            userserver.save()

            return await self.bot.send_message(
                message.channel,
                'Admin `{!s}` added to `{}` successfully'.format(
                    duser,
                    server.name
                )
            )

        elif usertype == 'blacklist':
            userserver.blacklisted = True
            userserver.save()

            return await self.bot.send_message(
                message.channel,
                'Blacklist `{!s}` added to `{}` successfully'.format(
                    duser,
                    server.name
                )
            )

        raise CommandException('Unknown user type `{}`'.format(usertype))

    def get_server(self, name, message):
        if name.lower() == 'here':
            if message.channel.is_private:
                raise CommandException(
                    "This command isn't supported for private channels"
                )

            return message.server

        server = self.bot.get_server(name)
        if server:
            return server

        gen = self.get_servers_with_permission(name, message.author)
        server = next(gen, None)

        if server:
            return server

        raise CommandException('Server `{}` not found'.format(name))

    def get_servers_with_permission(self, name, member):
        for server in self.bot.servers:
            if UserLevel.get(member, server) < self.user_level:
                continue

            if name in server.name:
                yield server

    def ensure_user(self, server, duser):
        user = self.bot.database.get_User_by_user_did(duser.id)

        if not user:
            user = self.bot.database.get_User()
            user.user_did = duser.id
            user.save()

        return user

    def get_discord_user(self, server, name):
        if name[0:3] == '<@!':
            retmember = server.get_member(name[3:-1])

        elif name[0:2] == '<@':
            retmember = server.get_member(name[2:-1])

        else:
            name = name.lower()

            for member in server.members:
                if name in str(member).lower():
                    retmember = member

        if retmember:
            return retmember

        raise CommandException('User `{}` not found'.format(name))

    def ensure_userserver(self, server, user):
        userserver = self.bot.database.get_UserServer()
        userserver = userserver.get_by(
            server_did=server.id,
            user_id=user.id
        )

        if not userserver:
            userserver = self.bot.database.get_UserServer()
            userserver.server_did = server.id
            userserver.user_id = user.id
            userserver.save()

        return userserver

    async def cmd_remove_user(self, message, username, usertype,
                              servername='here'):
        server = self.get_server(servername, message)
        duser = self.get_discord_user(server, username)
        user = self.ensure_user(server, duser)
        userserver = self.ensure_userserver(server, user)

        if usertype == 'admin':
            userserver.admin = False
            userserver.save()

            self.clean_up(user, userserver)

            return await self.bot.send_message(
                message.channel,
                'Admin `{!s}` removed from `{}` successfully'.format(
                    duser,
                    server.name
                )
            )

        elif usertype == 'blacklist':
            userserver.blacklisted = False
            userserver.save()

            self.clean_up(user, userserver)

            return await self.bot.send_message(
                message.channel,
                'Blacklist `{!s}` removed from `{}` successfully'.format(
                    duser,
                    server.name
                )
            )

        raise CommandException('Unknown user type `{}`'.format(usertype))

    def clean_up(self, user, userserver):
        if not userserver.admin and not userserver.blacklisted:
            userserver.delete()

        if not user.user_servers:
            user.delete()

    async def cmd_list_users(self, message, listtype='both', servername='',
                             username=''):
        users = self.bot.database.get_User_list()

        if servername:
            server = self.get_server(servername, message)
        else:
            server = None

        text = await self.get_list_text(users, username, listtype, server,
                                        message)

        await self.bot.send_message(message.channel, text)

    async def get_list_text(self, users, username, listtype, server, message):
        pieces = []

        for user in users:
            for userserver in user.user_servers:
                if not self.check_listtype(userserver, listtype):
                    continue

                if not self.check_server(userserver, server, message.author):
                    continue

                if not await self.check_username(user, username):
                    continue

                pieces.append(
                    await self.get_list_text_piece(user, userserver, server)
                )

        if not pieces:
            return 'No `users` found.'

        return '\u200C\n{}'.format('\n'.join(pieces))

    def check_listtype(self, userserver, listtype):
        if listtype == 'admin':
            return userserver.admin

        if listtype == 'blacklist':
            return userserver.blacklisted

        if listtype in ('', 'both'):
            return True

        raise CommandException('Unrecognised list type `{}`'.format(listtype))

    def check_server(self, userserver, server, member):
        if server and server.id != userserver.server_did:
            return False

        return UserLevel.get(member, userserver.server) >= self.user_level

    async def check_username(self, user, username):
        return username in str(await user.get_user())

    async def get_list_text_piece(self, user, userserver, server):
        piece = '`{!s}`'.format(await user.get_user())

        if userserver.admin:
            piece += ' `admin`'

        if userserver.blacklisted:
            piece += ' `blacklisted`'

        if not server:  # user didn't specify a specific server
            piece = '`{0.server.name}` {1}'.format(userserver, piece)

        return piece
