from discord.utils import cached_slot_property
from discord import NotFound, Forbidden
from ..model import Model


class UserGuild(Model):
    @cached_slot_property('_user')
    def user(self):
        return self.database.get_User_by_id(self.user_id)

    @cached_slot_property('_guild')
    def guild(self):
        try:
            return self.bot.get_guild(self.guild_did)

        except (NotFound, Forbidden):
            return None

    def define_table(self):
        return 'user_guilds'

    def define_fields(self):
        return {
            'user_id': None,
            'guild_did': None,
            'admin': False,
            'blacklisted': False,
        }
