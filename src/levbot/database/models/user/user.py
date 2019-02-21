import discord

from discord.utils import cached_slot_property
from ..model import Model
from ....user_level import UserLevel


class User(Model):
    @cached_slot_property('_user_servers')
    def user_servers(self):
        return self.database.get_UserServer_list_by_user_id(self.id)

    async def get_user(self):
        try:
            return self._user

        except AttributeError:
            self._user = await self.bot.get_user_info(self.user_did)
            return self._user

    def define_table(self):
        return 'users'

    def define_fields(self):
        return {
            'user_did': None,
            'global_admin': False,
            'blacklisted': False,
        }

    def is_admin(self, server):
        for user_server in self.user_servers:
            if user_server.server == server:
                return user_server.admin

        return False

    def is_blacklisted(self, server):
        for user_server in self.user_servers:
            if user_server.server == server:
                return user_server.blacklisted

        return False

    def get_user_level(self, channel=None):
        if channel:
            member = channel.server.get_member(self.user_did)
            if member:
                return UserLevel.get(member, channel)

        return UserLevel.get(discord.Object(self.user_did), channel)

    def save(self):
        super().save()

        for server in self.user_servers:
            server.user_id = self.id
            server.save()

    def delete(self):
        for server in self.user_servers:
            server.delete()

        super().delete()
