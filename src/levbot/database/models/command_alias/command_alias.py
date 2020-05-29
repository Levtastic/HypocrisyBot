from ..model import Model


class CommandAlias(Model):
    _table = 'command_aliases'

    _fields = (
        'command',
        'alias',
    )
