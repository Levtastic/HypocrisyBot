import sqlite3
import logging

from contextlib import closing
from .models import CommandAlias, User, UserGuild
from .commands.model_commands import ModelCommands
from .commands.user_commands import UserCommands


class Database:
    def __init__(self, bot, db_name):
        self.bot = bot

        self.database = sqlite3.connect(db_name)
        self.database.row_factory = sqlite3.Row

        self.model_commands = ModelCommands(bot, self)
        UserCommands(bot)

        self.models = {}
        self.add_models(CommandAlias, User, UserGuild)

        self._is_open = True

    @property
    def is_open(self):
        return self._is_open

    def close(self):
        if self.is_open:
            logging.info('Vacuuming and closing database')
            self.execute('VACUUM')
            self.database.close()
            self._is_open = False

    def force_update_model_tables(self):
        logging.info('Updating table layouts.')

        for name, model in self.models.items():
            logging.info(f' - {name}...')
            model._update_table()

        logging.info('Tables updated.')

    def add_models(self, *model_classes):
        for cls in model_classes:
            cls._init_class(self.bot, self)
            setattr(self, cls.__name__, cls)
            self.models[cls.__name__] = cls
            self.model_commands.register_model(cls.__name__)

    def table_exists(self, tablename):
        query = """
            SELECT
                COUNT(1)
            FROM
                sqlite_master
            WHERE
                    type = 'table'
                AND
                    name = ?
        """

        return int(self.fetch_value(query, tablename)) > 0

    def execute(self, query, parameters=(), script=False, commit=True):
        parameters = self._convert_parameters(parameters)

        with closing(self.database.cursor()) as cursor:
            if script:
                cursor.executescript(query)

            else:
                cursor.execute(query, parameters)

            if commit:
                self.database.commit()

            return cursor.lastrowid

    def _convert_parameters(self, parameters):
        if isinstance(parameters, (tuple, list, dict)):
            return parameters

        return (parameters, )

    def fetch_all(self, query, parameters=()):
        parameters = self._convert_parameters(parameters)

        with closing(self.database.cursor()) as cursor:
            cursor.execute(query, parameters)

            return cursor.fetchall()

    def fetch_row(self, query, parameters=()):
        parameters = self._convert_parameters(parameters)

        with closing(self.database.cursor()) as cursor:
            cursor.execute(query, parameters)

            return cursor.fetchone()

    def fetch_value(self, query, parameters=(), *args, **kwargs):
        try:
            return self.fetch_row(query, parameters)[0]

        except IndexError:
            if args:
                return args[0]

            return kwargs.get('default', None)

    def insert(self, table, fields):
        query = 'INSERT INTO {} ({}) VALUES ({})'

        fieldnames = fields.keys()

        query = query.format(
            table,
            ','.join(fieldnames),
            ','.join(':{}'.format(name) for name in fieldnames)
        )

        return self.execute(query, fields)

    def update(self, table, fields, where_query='', where_args={}, **kwargs):
        query = 'UPDATE {} SET {} WHERE {}'

        fieldnames = tuple(fields.keys())

        if where_query:
            fields.update(where_args)

        else:
            fields.update({
                'where_' + key: value for key, value in kwargs.items()
            })
            where_query = ' AND '.join(
                '{0} = :where_{0}'.format(name) for name in kwargs.keys()
            )

        query = query.format(
            table,
            ','.join('{0} = :{0}'.format(name) for name in fieldnames),
            where_query
        )

        return self.execute(query, fields)
