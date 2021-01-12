import asyncio
import aiohttp
import random
import logging

from .user_level import UserLevel
from discord import HTTPException, InvalidArgument


class AvatarManager:
    def __init__(self, bot, settings):
        self.bot = bot
        self.settings = settings

        if settings.url and settings.refresh_command:
            bot.commands.register_handler(
                settings.refresh_command,
                self.cmd_refresh_avatar,
                user_level=UserLevel.global_bot_admin,
                description=(
                    "Refreshes the bot's avatar, reloading it from"
                    ' the url given in the settings'
                )
            )

        if (settings.url and settings.random_change_min):
            self.bot.loop.create_task(self.avatar_loop())

    async def cmd_refresh_avatar(self, message):
        channel = message.channel

        with channel.typing():
            if await self.refresh_avatar():
                return await channel.send('Avatar refreshed.')

            else:
                return await channel.send('Unable to refresh avatar.')

    async def avatar_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            await self.refresh_avatar()

            if self.settings.random_change_max:
                await asyncio.sleep(random.uniform(
                    self.settings.random_change_min,
                    self.settings.random_change_max
                ) * 60)

            else:
                await asyncio.sleep(self.settings.random_change_min * 60)

    async def refresh_avatar(self):
        if not self.settings.url:
            raise KeyError('bot.avatar.url must be set to use this function')

        try:
            bavatar = await asyncio.wait_for(self.get_avatar_bytes(), 10)

        except asyncio.TimeoutError:
            logging.warning('Timed out while loading avatar bytes.')
            return False

        if not bavatar:
            return False

        try:
            if await asyncio.wait_for(self.set_avatar_bytes(bavatar), 10):
                logging.info('Avatar refreshed.')
                return True

        except asyncio.TimeoutError:
            logging.warning('Timed out while refreshing avatar.')

        return False

    async def get_avatar_bytes(self):
        url = self.settings.url.format(
            user_id=self.bot.user.id,
            random_seed=str(random.random())[2:]
        )

        logging.info(f'Fetching avatar from `{url}`')

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logging.warning(f'Received status {response.status}'
                                    f' from `{url}`')
                    return False

                return await response.read()

    async def set_avatar_bytes(self, bytes):
        try:
            await self.bot.user.edit(avatar=bytes)
            return True

        except (HTTPException, InvalidArgument) as ex:
            # status code 400 is returned if discord is rate limiting your avatar changes
            if isinstance(ex, HTTPException) and ex.status == 400:
                logging.warning(ex)
                return False

            savatar = str(bytes)
            savatar if len(savatar) <= 1000 else savatar[:997] + '...'
            logging.exception(savatar)
            return False
