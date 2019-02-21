from ..model import Model


class CommandAlias(Model):
    def define_table(self):
        return 'command_aliases'

    def define_fields(self):
        return (
            'command',
            'alias',
        )
