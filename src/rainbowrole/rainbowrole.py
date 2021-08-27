import asyncio

from discord import Colour
from levbot import UserLevel


class RainbowRole:
    colours = [
        Colour.from_rgb(234, 91, 12),
        Colour.from_rgb(243, 146, 0),
        Colour.from_rgb(255, 237, 0),
        Colour.from_rgb(149, 193, 31),
        Colour.from_rgb(58, 170, 53),
        Colour.from_rgb(0, 150, 64),
        Colour.from_rgb(0, 154, 147),
        Colour.from_rgb(0, 159, 227),
        Colour.from_rgb(0, 105, 180),
        Colour.from_rgb(0, 72, 153),
        Colour.from_rgb(49, 39, 131),
        Colour.from_rgb(102, 36, 131),
        Colour.from_rgb(149, 27, 129),
        Colour.from_rgb(230, 0, 126),
        Colour.from_rgb(229, 0, 81),
    ]

    def __init__(self, bot):
        self.bot = bot
        self.settings = bot.settings.rainbowrole
        self.is_running = False

        if self.settings.guild_id and self.settings.role_id:
            bot.register_event('on_ready', self.on_ready)

            bot.commands.register_handler(
                'brainwave',
                self.cmd_brainwave,
                user_level=UserLevel.guild_bot_admin
            )
            bot.commands.register_handler(
                'vaporwave',
                self.cmd_vaporwave,
                user_level=UserLevel.guild_bot_admin
            )
            bot.commands.register_handler(
                'randomwave',
                self.cmd_randomwave,
                user_level=UserLevel.guild_bot_admin
            )
            bot.commands.register_handler(
                'randomcolour',
                self.cmd_randomcolour,
                user_level=UserLevel.guild_bot_admin
            )
            bot.commands.register_handler(
                'nocolour',
                self.cmd_nocolour,
                user_level=UserLevel.guild_bot_admin
            )

    async def on_ready(self):
        self.guild = await self.bot.fetch_guild(self.settings.guild_id)
        self.role = self.guild.get_role(int(self.settings.role_id))

        self.bot.register_event('on_member_join', self.on_member_join)

    async def on_member_join(self, member):
        if member.guild == self.guild:
            await member.add_roles(
                self.role,
                reason='Automatically added on join'
            )

    async def cmd_brainwave(self, message, cycles='1'):
        """Makes a set role cycle through a list of colours once per second"""

        if self.is_running or message.guild != self.guild:
            return

        self.is_running = True

        cycles = self.get_cycles(cycles)

        for colour in self.colours * cycles:
            await asyncio.gather(
                self.role.edit(colour=colour),
                asyncio.sleep(1)
            )

        await self.role.edit(colour=Colour.default())

        self.is_running = False

    def get_cycles(self, cycles):
        try:
            cycles = int(cycles)
        except ValueError:
            cycles = 1

        return max(1, min(10, cycles))

    async def cmd_vaporwave(self, message, cycles='1'):
        """Makes a set role cycle through a list of colours once per minute"""

        if self.is_running or message.guild != self.guild:
            return

        self.is_running = True

        cycles = self.get_cycles(cycles)

        for colour in self.colours * cycles:
            await asyncio.gather(
                self.role.edit(colour=colour),
                asyncio.sleep(60)
            )

        await self.role.edit(colour=Colour.default())

        self.is_running = False

    async def cmd_randomwave(self, message, cycles='1'):
        """Makes a set role cycle through random colours once per second"""

        if self.is_running or message.guild != self.guild:
            return

        self.is_running = True

        cycles = self.get_cycles(cycles)

        for _ in range(len(self.colours) * cycles):
            await asyncio.gather(
                self.role.edit(colour=Colour.random()),
                asyncio.sleep(1)
            )

        await self.role.edit(colour=Colour.default())

        self.is_running = False

    async def cmd_randomcolour(self, message):
        """Makes a set role set to a random colour"""

        if self.is_running or message.guild != self.guild:
            return

        await self.role.edit(colour=Colour.random())

    async def cmd_nocolour(self, message):
        """Makes a set role set to no colour"""

        if self.is_running or message.guild != self.guild:
            return

        await self.role.edit(colour=Colour.default())
