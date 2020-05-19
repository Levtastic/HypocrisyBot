import inspect

from discord.abc import PrivateChannel
from ..user_level import UserLevel
from . import CommandDispatcher, Handler
from . import handlers


class Commands:
    def __init__(self, bot, *, loop=None):
        self.bot = bot
        self.root = CommandDispatcher(bot, '__root__', loop=loop)

        self._register_sub_handlers()

        bot.register_event('on_message', self._on_message)

    def _register_sub_handlers(self):
        for sub_handler in dir(handlers):
            if not sub_handler[0].isupper():
                continue

            getattr(handlers, sub_handler)(self)

    def register_handler(self, command, coroutine, **kwargs):
        handler = self.build_handler(command, coroutine, **kwargs)
        return self.root.register_handler(handler, command)

    def build_handler(self, command, coroutine, **kwargs):
        defaults = {
            'user_level': UserLevel.guild_bot_admin,
            'description': inspect.getdoc(coroutine) or '',
            'syntax': self.get_syntax_for(coroutine, command),
        }

        defaults.update(kwargs)

        return Handler(coroutine, **defaults)

    def get_syntax_for(self, coroutine, command):
        parameters = list(inspect.signature(coroutine).parameters.values())

        return '{} {}'.format(
            command,
            ' '.join(self._get_parameter_syntax(p) for p in parameters[1:])
        )

    def _get_parameter_syntax(self, parameter):
        if parameter.default == parameter.empty:
            fmt = '<{0.name}>'
        elif parameter.default is '':
            fmt = '<{0.name} (optional)>'
        else:
            fmt = '<{0.name} (default: "{0.default}")>'

        return fmt.format(parameter)

    async def _on_message(self, message):
        command = self._get_command(message)

        if command:
            return self.root.dispatch(command, message)

        return False

    def _get_command(self, message):
        prefixes = (
            '<@{.id}>'.format(self.bot.user),  # standard mention
            '<@!{.id}>'.format(self.bot.user)  # nickname mention
        )

        for prefix in prefixes:
            if message.content.startswith(prefix):
                return message.content[len(prefix):].lstrip()

        if isinstance(message.channel, PrivateChannel):
            return message.content

        return ''
