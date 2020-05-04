from functools import partial
from sqlite3 import IntegrityError
from ...user_level import UserLevel
from ...commands import CommandException


class ModelCommands:
    def __init__(self, bot, database):
        self.bot = bot
        self.database = database

    def register_model(self, model):
        for command in ('add', 'edit', 'remove', 'list'):
            self.bot.commands.register_handler(
                '{} {}'.format(command, model),
                self.get_partial(command, model),
                user_level=UserLevel.global_bot_admin,
                description=self.get_description(command, model),
                syntax=self.get_syntax(command, model)
            )

    def get_partial(self, command, model):
        func_name = 'cmd_{}'.format(command)
        native_func = getattr(self, func_name)
        partial_func = partial(native_func, model)
        partial_func.__doc__ = native_func.__doc__
        return partial_func

    def get_description(self, command, model_name):
        fmt = 'Manually {} a {} model {} the database'

        if command == 'add':
            return fmt.format('adds', model_name, 'to')

        elif command == 'edit':
            return fmt.format('edits', model_name, 'in')

        elif command == 'remove':
            return fmt.format('removes', model_name, 'from')

        elif command == 'list':
            return 'Lists all {} models in the database'.format(model_name)

        return ''

    def get_model(self, model_name):
        factory_name = 'get_{}'.format(model_name)
        factory = getattr(self.database, factory_name)
        return factory()

    def get_syntax(self, command, model_name):
        model = self.get_model(model_name)

        fields = ''
        if command == 'edit':
            fields = '<search_key> = <search_value> '

        if command in ('remove', 'list'):
            fields += '<key> = <value>'

        else:
            fields += ', '.join(
                '{} = <value>'.format(field) for field in model.fields
            )

        return '{} {} {}'.format(command, model_name, fields)

    async def cmd_add(self, model_name, message, attributes):
        model = self.get_model(model_name)

        syntax_message = self.get_syntax('add', model_name)

        try:
            pairs = list(self.get_attribute_pairs(attributes, model))

        except ValueError:
            raise CommandException(syntax_message)

        if not pairs:
            raise CommandException(syntax_message)

        self.set_model_attributes(model, pairs)

        try:
            model.save()

        except IntegrityError:
            raise CommandException(
                'One or more required fields were left out of the command'
            )

        await message.channel.send(
            '`{}` `({})` added'.format(
                model_name,
                model.id
            )
        )

    def get_attribute_pairs(self, attributes, model, count_override=None):
        count = (count_override or len(model.fields)) - 1

        for pair in attributes.split(',', count):
            field, value = pair.split('=', 1)
            field, value = field.strip(), value.strip()

            if field not in model.fields and field != 'id':
                raise CommandException('Unrecognised field `{}`'.format(field))

            yield field, value

    def set_model_attributes(self, model, pairs):
        for field, value in pairs:
            setattr(model, field, value)

    async def cmd_edit(self, model_name, message, attributes):
        model = self.get_model(model_name)

        syntax_message = self.get_syntax('edit', model_name)

        try:
            print(repr(attributes))
            pairs = list(self.get_attribute_pairs(
                attributes,
                model
            ))

        except ValueError:
            raise CommandException(syntax_message)

        if len(pairs) < 2:
            raise CommandException(syntax_message)

        model = self.search_for_model(model, *pairs.pop(0))

        self.set_model_attributes(model, pairs)

        model.save()

        await message.channel.send(
            '`{}` `({})` edited'.format(
                model_name,
                model.id
            )
        )

    def search_for_model(self, model, field, value):
        models = model.get_list_by(**{field: value})

        if not models:
            raise CommandException(
                'No {} models found with these parameters'.format(
                    type(model).__name__
                )
            )

        if len(models) != 1:
            raise CommandException(
                ('This operation only works on one {} at a time,'
                 ' but we found {}').format(
                    type(model).__name__,
                    len(models)
                )
            )

        return models[0]

    async def cmd_remove(self, model_name, message, attributes):
        model = self.get_model(model_name)

        syntax_message = self.get_syntax('remove', model_name)

        try:
            pairs = list(self.get_attribute_pairs(attributes, model))

        except ValueError:
            raise CommandException(syntax_message)

        if len(pairs) != 1:
            raise CommandException(syntax_message)

        model = self.search_for_model(model, *pairs[0])

        model.delete()

        await message.channel.send(
            '`{}` deleted'.format(model_name)
        )

    async def cmd_list(self, model_name, message, attributes=''):
        model = self.get_model(model_name)

        if attributes:
            try:
                pairs = list(self.get_attribute_pairs(attributes, model))

            except ValueError:
                raise CommandException(self.get_syntax('list', model_name))

        else:
            pairs = []

        models = self.filter_model(model, pairs)

        if not models:
            return await message.channel.send(
                'No `{}` records found'.format(model_name)
            )

        await message.channel.send(
            '\u200C\n' + '\n'.join(str(model) for model in models)
        )

    def filter_model(self, model, pairs):
        if pairs:
            list_filter = {field: value for field, value in pairs}
            return model.get_list_by(**list_filter)

        return model.get_all()
