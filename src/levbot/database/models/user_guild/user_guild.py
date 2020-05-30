from discord.utils import cached_slot_property
from discord import NotFound, Forbidden
from ..model import Model, Required


class UserGuild(Model):
    _table = 'user_guilds'

    _fields = {
        'user_id': Required(int),
        'guild_did': Required(int),
        'admin': False,
        'blacklisted': False,
    }

    _indexes = ['user_id']

    def __del__(self):
        if self.id is None:
            return

        if not self.admin and not self.blacklisted:
            self.delete()

            if not self.user.user_guilds:
                self.user.delete()

    @cached_slot_property('_user')
    def user(self):
        return self.database.User.get_by(id=self.user_id)

    @cached_slot_property('_guild')
    def guild(self):
        try:
            return self.bot.get_guild(self.guild_did)

        except (NotFound, Forbidden):
            return None
