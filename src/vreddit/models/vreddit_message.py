from levbot.database import Model
from discord import NotFound, Forbidden


class VRedditMessage(Model):
    def define_table(self):
        return 'vreddit_message'

    def define_fields(self):
        return {
            'src_url': None,
            'channel_did': None,
            'src_message_did': None,
            'dest_message_did': '',
        }

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
            self._src_message = await self.bot.get_message(
                self.get_channel(),
                self.src_message_did
            )
            return self._src_message

    async def get_dest_message(self):
        if not self.dest_message_did:
            return None

        try:
            return self._dest_message

        except AttributeError:
            self._dest_message = await self.bot.get_message(
                self.get_channel(),
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
                await self.bot.delete_message(message)

        except (NotFound, Forbidden):
            pass
