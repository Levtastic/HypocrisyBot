import aiohttp
import logging

from levbot import UserLevel, TypingContext
from discord import HTTPException, InvalidArgument


class FaceAvatars:
    def __init__(self, bot):
        self.bot = bot
        self.url = 'https://thispersondoesnotexist.com/'

        bot.register_event('on_ready', self.on_ready)

        bot.commands.register_handler(
            'refresh avatar',
            self.cmd_refresh_avatar,
            user_level=UserLevel.global_bot_admin,
            description=(
                'Fetches a new random face and sets it as the bot avatar'
            )
        )

    async def on_ready(self):
        if not await self.get_new_avatar():
            logging.info('Startup face change failed')

    async def get_new_avatar(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as resp:
                if resp.status != 200:
                    return False

                bavatar = await resp.read()

        try:
            await self.bot.edit_profile(
                avatar=bavatar
            )

        except (HTTPException, InvalidArgument):
            logging.exception(bavatar)
            return False

        logging.info('New face avatar set.')

        return True

    async def cmd_refresh_avatar(self, message):
        with TypingContext(message.channel):
            if await self.get_new_avatar():
                response = 'Roger that boss, face changed'

            else:
                response = "Sorry boss, can't change my face right now"

        await self.bot.send_message(message.channel, response)
