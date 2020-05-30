from ..model import Model, Required


class CommandAlias(Model):
    _table = 'command_aliases'

    _fields = {
        'command': Required(str),
        'alias': Required(str),
    }

    _indexes = ['alias']
