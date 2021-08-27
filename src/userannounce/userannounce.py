class UserAnnounce:
    def __init__(self, bot):
        self.bot = bot
        self.settings = bot.settings.userannounce

        if self.settings.channel_id:
            bot.register_event('on_ready', self.on_ready)

    async def on_ready(self):
        self.channel = await self.bot.fetch_channel(self.settings.channel_id)
        self.bot.register_event('on_member_join', self.on_member_join)
        self.bot.register_event('on_member_remove', self.on_member_remove)

    async def on_member_join(self, member):
        if member.guild == self.channel.guild:
            await self.channel.send(
                f'{member} (<@{member.id}>) has joined the server')

    async def on_member_remove(self, member):
        if member.guild == self.channel.guild:
            await self.channel.send(
                f'{member} (<@{member.id}>) has left the server')
