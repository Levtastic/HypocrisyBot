from levbot.database import Model, Required, Optional
from discord import NotFound, Forbidden


class VRedditMessage(Model):
    _table = 'vreddit_message'

    _fields = {
        'src_url': Required(str),
        'channel_did': Required(int),
        'src_message_did': Required(int),
        'dest_message_did': Optional(int),
    }

    _indexes = [
        ['channel_did', 'src_message_did',],
        ['channel_did', 'dest_message_did'],
    ]

    def get_channel(self):
        try:
            return self._channel

        except AttributeError:
            self._channel = self.bot.get_channel(self.channel_did)
            return self._channel

    async def get_src_message(self):
        try:
            return self._src_message

        except AttributeError:
            self._src_message = await self.get_channel().fetch_message(
                self.src_message_did
            )
            return self._src_message

    async def get_dest_message(self):
        if not self.dest_message_did:
            return None

        try:
            return self._dest_message

        except AttributeError:
            self._dest_message = await self.get_channel().fetch_message(
                self.dest_message_did
            )
            return self._dest_message

    def delete(self, delete_discord_message=True):
        if delete_discord_message:
            self.bot.loop.create_task(self.delete_message())

        super().delete()

    async def delete_message(self):
        try:
            message = await self.get_dest_message()
            if message:
                await message.delete()

        except (NotFound, Forbidden):
            pass
