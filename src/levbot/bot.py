import asyncio
import logging
import sys
import os

from collections import defaultdict
from discord import Client
from discord.abc import Messageable
from .console_input import ConsoleInput
from .logging_config import set_up_logging, remove_pushbullet_logger
from .database import Database
from .commands import Commands
from .avatar_manager import AvatarManager
from . import user_level, send_splitter


class Bot(Client):
    def __init__(self, settings={}, console_variables={}):
        super().__init__()

        self.settings = settings
        self.main_settings = settings.bot

        self.logger = set_up_logging(settings.bot.logs)

        self._event_handlers = defaultdict(list)
        self.commands = Commands(self)
        self.database = Database(self, self.main_settings.db_name)
        self.avatar_manager = AvatarManager(self, settings.bot.avatar)

        user_level.owner_usernames = self.main_settings.owner_usernames
        user_level.database = self.database

        console_variables['bot'] = self
        ConsoleInput(self, console_variables)

        if settings.bot.message_splitting.enabled:
            send_splitter.wrap(Messageable, settings.bot.message_splitting)

    async def close(self):
        remove_pushbullet_logger()
        await super().close()
        self.database.close()

    def run(self, *args, **kwargs):
        super().run(self.main_settings.token, *args, **kwargs)

    async def restart(self, after=0):
        await asyncio.sleep(after)
        await self.close()

        pyexec = sys.executable
        os.execl(pyexec, pyexec, *sys.argv)

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
