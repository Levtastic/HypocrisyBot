import abc
import inspect
import logging

from types import MappingProxyType


class Model(abc.ABC):
    # these two attributes are to be overridden in child classes
    _table = None
    _fields = None

    def __init__(self):
        self._id = None

        for field, default in self.fields.items():
            setattr(self, field, default)

    def __repr__(self):
        objfmt = '{name} `({id!r})`: {fields}'
        fieldfmt = '`{f}` = `{v!r}`'

        name = type(self).__name__
        dbid = self.id
        fields = ', '.join(
            fieldfmt.format(f=f, v=getattr(self, f)) for f in self.fields
        )

        return objfmt.format(name=name, id=dbid, fields=fields)

    @classmethod
    def _init_class(cls, bot, database):
        cls.bot = bot
        cls.database = database

        cls._check_attributes()
        cls._init_fields()

        cls._build_table_if_necessary()
        cls._update_table_if_necessary()

    @classmethod
    def _check_attributes(cls):
        if cls._table is None or cls._fields is None:
            raise AttributeError(f'Child model `{cls.__name__}` must provide'
                                  ' `_table` and `_fields` attributes')

    @classmethod
    def _init_fields(cls):
        fields = cls._fields

        if not isinstance(fields, dict):
            fields = {field: None for field in fields}

        cls._fields = MappingProxyType(fields)

    @classmethod
    def _build_table_if_necessary(cls):
        if not cls.has_table():
            cls._build_table()

    @classmethod
    def has_table(cls):
        return cls.database.table_exists(cls._table)

    @classmethod
    def _build_table(cls):
        with open(inspect.getfile(cls)[:-3] + '.sql', 'r') as file:
            cls.database.execute(file.read(), script=True)

    @classmethod
    def _update_table_if_necessary(cls):
        if cls._needs_new_columns():
            cls._update_table()

    @classmethod
    def _needs_new_columns(cls):
        query = """
            pragma table_info('{}')
        """.format(
            cls._table
        )

        fields = [f['name'] for f in cls.database.fetch_all(query)]
        fields.remove('id')

        return set(fields) != set(cls._fields.keys())

    @classmethod
    def _update_table(cls):
        old_data = cls._get_old_data()

        cls._delete_table()
        cls._build_table()

        for row in old_data:
            fields = dict(cls._fields)
            fields.update(row)

            cls.database.insert(cls._table, fields)

    @classmethod
    def _get_old_data(cls):
        query = """
            SELECT
                *
            FROM
                {}
            ORDER BY
                id ASC
        """.format(
            cls._table
        )

        return cls.database.fetch_all(query)

    @classmethod
    def _delete_table(cls):
        query = """
            DROP TABLE
                {}
        """.format(
            cls._table
        )

        cls.database.execute(query, commit=False)

    @classmethod
    def get_list_by(cls, **kwargs):
        if not kwargs:
            return cls.get_list()

        all_fields = list(cls._fields) + ['id']

        for field in kwargs:
            if field not in all_fields:
                raise AttributeError(
                    'Field "{}" not found in model "{}"'.format(
                        field,
                        cls.__name__
                    )
                )

        query = """
            SELECT
                *
            FROM
                {}
            WHERE
                {}
        """.format(
            cls._table,
            ' AND '.join('{0} = :{0}'.format(name) for name in kwargs)
        )
        data = cls.database.fetch_all(query, kwargs)

        return [cls._build_from_fields(fields) for fields in data]

    @classmethod
    def _build_from_fields(cls, fields):
        fields = dict(fields)

        model = cls()
        model._id = fields.pop('id')
        for field in model.fields:
            value = fields.pop(field)

            if type(getattr(model, field)) is bool:
                value = bool(value)

            setattr(model, field, value)

        if fields:
            logging.warning('{} has extra fields in the database: {!r}'.format(
                cls.__name__,
                fields
            ))

        return model

    @classmethod
    def get_list(cls, order_by='id ASC', limit=None):
        query = """
            SELECT
                *
            FROM
                {}
            ORDER BY
                {}
        """.format(cls._table, order_by)

        if limit is not None:
            query += 'LIMIT {}'.format(limit)

        data = cls.database.fetch_all(query)

        return [cls._build_from_fields(fields) for fields in data]

    @classmethod
    def get_by(cls, **kwargs):
        models = cls.get_list_by(**kwargs)
        return models[0] if models else None

    @property
    def id(self):
        return self._id

    @property
    def table(self):
        return self._table

    @property
    def fields(self):
        return self._fields

    def save(self):
        fields = {field: getattr(self, field) for field in self.fields}

        if self.id is None:
            self._id = self.database.insert(self.table, fields)

        else:
            self.database.update(self.table, fields, id=self.id)

    def delete(self):
        if not self.id:
            return

        query = """
            DELETE FROM
                {}
            WHERE
                id = ?
        """.format(self.table)

        self.database.execute(query, self.id)
        self._id = None

    def exists(self):
        if not self.id:
            return False

        query = """
            SELECT
                COUNT(1)
            FROM
                {}
            WHERE
                id = ?
        """.format(self.table)

        return int(self.database.fetch_value(query, self.id)) > 0
