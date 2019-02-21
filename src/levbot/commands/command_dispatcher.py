import inspect
import logging
import asyncio

from types import MappingProxyType
from collections import namedtuple
from ..user_level import UserLevel


Handler = namedtuple('Handler', (
    'coroutine',
    'user_level',
    'description',
    'syntax',
))


class CommandDispatcher:
    def __init__(self, bot, command, *, loop=None):
        self._bot = bot
        self._command = command
        self._child_dispatchers = {}
        self._handlers = []

        self.loop = loop or asyncio.get_event_loop()

        self.child_dispatchers = MappingProxyType(self._child_dispatchers)

    @property
    def command(self):
        return self._command

    @property
    def handlers(self):
        return list(self._handlers)

    @property
    def user_level(self):
        levels = []

        if self._handlers:
            levels += [h.user_level for h in self._handlers]

        if self.child_dispatchers:
            levels += [c.user_level for c in self.child_dispatchers.values()]

        levels = filter(None.__ne__, levels)

        return min(levels) if levels else None

    @property
    def is_leaf(self):
        return not self.child_dispatchers

    def ensure_child_dispatchers(self, commands):
        command, sub_commands = (commands.split(' ', 1) + [''])[:2]
        dispatcher = self._ensure_child_dispatcher(command)

        if sub_commands:
            return dispatcher.ensure_child_dispatchers(sub_commands)

        return dispatcher

    def _ensure_child_dispatcher(self, command):
        if command not in self._child_dispatchers:
            dispatcher = self.__class__(self._bot, command)
            self._child_dispatchers[command] = dispatcher

        return self._child_dispatchers[command]

    def register_handler(self, handler, command=None):
        if not command:
            self._handlers.append(handler)
            return self

        return self.ensure_child_dispatchers(command).register_handler(handler)

    def get(self, command_text, user_level):
        command, sub_commands = (command_text.split(' ', 1) + [''])[:2]
        command = self._get_command_from_alias(command)

        try:
            dispatcher = self.child_dispatchers[command]
            if dispatcher.user_level <= user_level:
                return dispatcher.get(sub_commands, user_level)

        except KeyError:
            pass

        return (self, command_text)

    def _get_command_from_alias(self, command):
        alias = self._bot.database.get_CommandAlias_by_alias(command)
        return alias.command if alias else command

    def dispatch(self, command, message):
        user_level = UserLevel.get(message.author, message.channel)
        dispatcher, attributes = self.get(command, user_level)
        handlers = [h
                    for h
                    in dispatcher.handlers
                    if h.user_level <= user_level]

        for handler in handlers:
            self.loop.create_task(self._wrapper(
                handler,
                attributes,
                message,
                command
            ))

        return bool(handlers)

    async def _wrapper(self, handler, attributes, message, command):
        try:
            binding = self._get_binding_for(handler, attributes, message)
            await handler.coroutine(*binding.args, **binding.kwargs)

        except CommandException as ex:
            await self._bot.send_message(message.channel, str(ex))

        except BaseException:
            await self._bot.send_message(
                message.channel,
                'Oh no, something went horribly wrong trying to complete this'
                ' command. Please tell the owner of this bot what command you'
                ' entered and roughly when this happened, and I\'ll get all'
                ' fixed up as soon as possible. Thanks!'
            )

            logging.exception(
                'Error in command {} {}'.format(command, attributes)
            )

    def _get_binding_for(self, handler, attributes, message):
        signature = inspect.signature(handler.coroutine)

        try:
            if len(signature.parameters) > 1:
                attributes = attributes.split(
                    ' ',
                    len(signature.parameters) - 2
                )
                return signature.bind(
                    message,
                    *[att for att in attributes if att is not '']
                )

            return signature.bind(message)

        except TypeError:
            raise CommandException('Syntax: `{}`'.format(handler.syntax))


class CommandException(Exception):
    pass
