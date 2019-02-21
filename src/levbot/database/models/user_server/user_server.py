from discord.utils import cached_slot_property
from discord import NotFound, Forbidden
from ..model import Model


class UserServer(Model):
    @cached_slot_property('_user')
    def user(self):
        return self.database.get_User_by_id(self.user_id)

    @cached_slot_property('_server')
    def server(self):
        try:
            return self.bot.get_server(self.server_did)

        except (NotFound, Forbidden):
            return None

    def define_table(self):
        return 'user_servers'

    def define_fields(self):
        return {
            'user_id': None,
            'server_did': None,
            'admin': False,
            'blacklisted': False,
        }
