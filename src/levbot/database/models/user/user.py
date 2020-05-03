import discord

from discord.utils import cached_slot_property
from ..model import Model
from ....user_level import UserLevel


class User(Model):
    @cached_slot_property('_user_guilds')
    def user_guilds(self):
        return self.database.get_UserGuild_list_by_user_id(self.id)

    async def get_user(self):
        try:
            return self._user

        except AttributeError:
            self._user = await self.bot.fetch_user(self.user_did)
            return self._user

    def define_table(self):
        return 'users'

    def define_fields(self):
        return {
            'user_did': None,
            'global_admin': False,
            'blacklisted': False,
        }

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
