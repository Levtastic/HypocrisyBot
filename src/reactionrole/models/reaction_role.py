from levbot.database import Model, Required


class ReactionRole(Model):
    _table = 'reaction_roles'

    _fields = {
        'channel_did': Required(int),
        'message_did': Required(int),
        'emoji': Required(str),
        'role_did': Required(int),
    }

    _indexes = [
        ['message_did', 'emoji'],
    ]

    @property
    def channel(self):
        return self.bot.get_channel(self.channel_did)

    @property
    def guild(self):
        return self.channel.guild

    @property
    def role(self):
        return self.guild.get_role(self.role_did)
