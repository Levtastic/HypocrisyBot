import discord

from discord.utils import cached_slot_property
from ..model import Model, Required
from ....user_level import UserLevel


class User(Model):
    _table = 'users'

    _fields = {
        'user_did': Required(int),
        'global_admin': False,
        'blacklisted': False,
    }

    _indexes = ['user_did']

    @cached_slot_property('_user_guilds')
    def user_guilds(self):
        return self.database.UserGuild.get_list_by(user_id=self.id)

    async def get_user(self):
        try:
            return self._user

        except AttributeError:
            self._user = await self.bot.fetch_user(self.user_did)
            return self._user

    def is_admin(self, guild):
        for user_guild in self.user_guilds:
            if user_guild.guild == guild:
                return user_guild.admin

        return False

    def is_blacklisted(self, guild):
        for user_guild in self.user_guilds:
            if user_guild.guild == guild:
                return user_guild.blacklisted

        return False

    def get_user_level(self, channel=None):
        if channel:
            member = channel.guild.get_member(self.user_did)
            if member:
                return UserLevel.get(member, channel)

        return UserLevel.get(discord.Object(self.user_did), channel)

    def save(self):
        super().save()

        for guild in self.user_guilds:
            guild.user_id = self.id
            guild.save()

    def delete(self):
        for guild in self.user_guilds:
            guild.delete()

        super().delete()
