import asyncio
import logging

from collections import defaultdict
from discord import Client
from .console_input import ConsoleInput
from .logging_config import set_up_logging, remove_pushbullet_logger
from .database import Database
from .commands import Commands
from . import user_level


class Bot(Client):
    def __init__(self, settings={}, console_variables={}):
        super().__init__()

        self.settings = settings

        self.bot_token = settings.pop('bot_token')
        self.pushbullet_token = settings.get('pushbullet_token', None)

        self.max_message_len = 2000
        self.newline_search_len = 200
        self.space_search_len = 100

        self._event_handlers = defaultdict(list)
        self.commands = Commands(self)
        self.database = Database(self, settings.get('db_name', 'levbot.db'))

        user_level.owner_usernames = settings.get('owner_usernames', [])
        user_level.database = self.database

        console_variables['bot'] = self
        ConsoleInput(self, console_variables)

    def run(self, *args, **kwargs):
        set_up_logging(self.pushbullet_token)
        super().run(self.bot_token, *args, **kwargs)
        remove_pushbullet_logger()

    def event(self, event_name=''):
        def decorator_event(coro):
            self.register_event(event_name or coro.__name__, coro)
            return coro

        return decorator_event

    def register_event(self, event, coro):
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('Events must be coroutine functions')

        self._event_handlers[event].append(coro)
        logging.debug(f'{event} registered')

    def unregister_event(self, event, coro):
        if event not in self._event_handlers \
           or coro not in self._event_handlers[event]:
            logging.debug(f'{event} unable to be unregistered')
            return

        self._event_handlers[event].remove(coro)
        logging.debug(f'{event} unregistered')

    def dispatch(self, event, *args, **kwargs):
        super().dispatch(event, *args, **kwargs)

        for handler in self._event_handlers['on_' + event]:
            self.loop.create_task(handler(*args, **kwargs))
