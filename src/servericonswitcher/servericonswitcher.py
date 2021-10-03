import asyncio
import random
import logging

from discord import Forbidden, HTTPException
from levbot import UserLevel


class ServerIconSwitcher:
    def __init__(self, bot):
        self.bot = bot
        self.settings = bot.settings.servericonswitcher

        if (self.settings.guild_id and self.settings.image_1
                and self.settings.image_2 and self.settings.image_3):
            bot.register_event('on_ready', self.on_ready)

    async def on_ready(self):
        self.guild = await self.bot.fetch_guild(self.settings.guild_id)
        self.bot.loop.create_task(self.servericon_loop())

        self.bot.commands.register_handler(
            'flash icon',
            self.cmd_flash_icon,
            user_level=UserLevel.guild_bot_admin,
            description='Flashes the server icon using ServerIconSwitcher'
        )

    async def cmd_flash_icon(self, message):
        if message.guild == self.guild:
            await self.flash_icon()

    async def servericon_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            await self.flash_icon()

            await asyncio.sleep(
                random.uniform(*self.settings.between_switches))

    async def flash_icon(self):
        if random.uniform(1, 100) <= self.settings.image_2_chance:
            await self.set_icon(self.settings.image_2)
        else:
            await self.set_icon(self.settings.image_3)

        await asyncio.sleep(
            random.uniform(*self.settings.switch_length))

        await self.set_icon(self.settings.image_1)

    async def set_icon(self, icon_file):
        with open(icon_file, 'rb') as f:
            icon = f.read()

        try:
            await self.guild.edit(icon=icon)
            logging.info('Server icon set to "%s"', icon_file)

        except (Forbidden, HTTPException):
            logging.exception('Unable to set server icon to "%s"', icon_file)
