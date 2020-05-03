from ...user_level import UserLevel


class HelpCommands:
    def __init__(self, commands):
        self.commands = commands
        self.bot = commands.bot

        self.register()

    def register(self):
        self.commands.register_handler(
            'help',
            self.cmd_help,
            user_level=UserLevel.user,
            description=(
                'Offers help on other commands, and lists sub-commands'
            )
        )

    async def cmd_help(self, message, command=''):
        user_level = UserLevel.get(message.author, message.channel)
        dispatcher, remainder = self.commands.root.get(command, user_level)
        command = self.strip_command(command, remainder)

        help_text_pieces = (
            self.get_name_and_level_text(command, dispatcher),
            self.get_syntax_text(dispatcher),
            self.get_description_text(dispatcher),
            self.get_subcommands_text(command, dispatcher, user_level),
        )

        await message.author.send('\n\n'.join(
            piece for piece in help_text_pieces if piece
        ))

    def strip_command(self, command, remainder):
        if remainder:
            return command[:-len(remainder)].strip()

        return command.strip()

    def get_name_and_level_text(self, command, dispatcher):
        if command:
            return (
                '`{0}`\n'
                'Minimum required level: {1.name}'
            ).format(command, dispatcher.user_level)

        return None

    def get_syntax_text(self, dispatcher):
        fmt = 'Syntax: `{}`'

        return '\n'.join(
            fmt.format(handler.syntax) for handler in dispatcher.handlers
        )

    def get_description_text(self, dispatcher):
        descriptions = self.get_comment_description_pieces(dispatcher)
        description_text = '\n{}\n'.format('-' * 50).join(descriptions)

        if description_text:
            return '**Description:**\n' + description_text

        return None

    def get_comment_description_pieces(self, dispatcher):
        for handler in dispatcher.handlers:
            if handler.description:
                yield handler.description

    def get_subcommands_text(self, command, dispatcher, user_level):
        if command:
            command = command + ' '

        subcmds = self.get_sub_command_names(dispatcher, user_level)
        subcmds_text = '\n'.join(
            '{}{}'.format(command, subcmd) for subcmd in subcmds
        )

        if subcmds_text:
            return (
                '**Commands**:\n'
                '{}\n\n'
                'Use `help {}<command>` for more information'
            ).format(subcmds_text, command)

        return None

    def get_sub_command_names(self, dispatcher, user_level):
        names = []

        for key, value in dispatcher.child_dispatchers.items():
            if value.user_level <= user_level:
                names.append(self.get_full_command_name(key, value))

        return names

    def get_full_command_name(self, name, dispatcher):
        if len(dispatcher.child_dispatchers) == 1:
            child = list(dispatcher.child_dispatchers.items())[0]
            return '{} {}'.format(name, self.get_full_command_name(*child))

        return name
