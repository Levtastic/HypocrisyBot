import asyncio
import aiohttp
import random
import logging

from levbot import UserLevel, TypingContext
from discord import HTTPException, InvalidArgument


class FaceAvatars:
    def __init__(self, bot):
        self.bot = bot
        self.url = 'https://thispersondoesnotexist.com/image'

        bot.commands.register_handler(
            'refresh avatar',
            self.cmd_refresh_avatar,
            user_level=UserLevel.global_bot_admin,
            description=(
                'Fetches a new random face and sets it as the bot avatar'
            )
        )

        self.bot.loop.create_task(self.avatar_loop())

    async def avatar_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed:
            if random.randint(1, 60 * 24) == 1:
                await self.get_new_avatar()

            await asyncio.sleep(60)

    async def get_new_avatar(self):
        try:
            bavatar = await asyncio.wait_for(self.get_face_image(), 10)

        except asyncio.TimeoutError:
            logging.info('Timed out fetching new face')
            return False

        if not bavatar:
            return False

        try:
            if await asyncio.wait_for(self.set_avatar(bavatar), 10):
                logging.info('New face avatar set.')
                return True

        except asyncio.TimeoutError:
            logging.info('Timed out setting new face')

        return False

    async def get_face_image(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as resp:
                if resp.status != 200:
                    logging.warning(
                        f'Received status {resp.status} from {self.url}')
                    return False

                return await resp.read()

    async def set_avatar(self, avatar):
        try:
            await self.bot.edit_profile(avatar=avatar)
            return True

        except (HTTPException, InvalidArgument) as ex:
            savatar = str(avatar)
            savatar if len(savatar) <= 1000 else savatar[:1000] + '...'
            logging.exception(savatar)
            return False

    async def cmd_refresh_avatar(self, message):
        with TypingContext(message.channel):
            if await self.get_new_avatar():
                response = 'Roger that boss, face changed'

            else:
                response = "Sorry boss, can't change my face right now"

        await self.bot.send_message(message.channel, response)
