import inspect
import logging

from types import MappingProxyType


class Model(object):
    # These attributes are tracked at the class-level, not the object-level
    _table_exists = False
    _table_up_to_date = False

    def __init__(self, bot, database):
        self.bot = bot
        self.database = database

        self._init_attributes()
        self._build_table_if_necessary()
        self._update_table_if_necessary()

    def __getattr__(self, name):
        if name.startswith('get_list_by_'):
            return lambda value: self.get_list_by(**{name[12:]: value})

        if name.startswith('get_by_'):
            return lambda value: self.get_by(**{name[7:]: value})

        raise AttributeError("'{}' object has no attribute '{}'".format(
            type(self).__name__,
            name
        ))

    def __repr__(self):
        objfmt = '{name} `({id!r})`: {fields}'
        fieldfmt = '`{f}` = `{v!r}`'

        name = type(self).__name__
        dbid = self.id
        fields = ', '.join(
            fieldfmt.format(f=f, v=getattr(self, f)) for f in self.fields
        )

        return objfmt.format(name=name, id=dbid, fields=fields)

    @property
    def id(self):
        return self._id

    @property
    def table(self):
        return self._table

    @property
    def fields(self):
        return self._fields

    def _init_attributes(self):
        self._init_id()
        self._init_table()
        self._init_fields()

    def _init_id(self):
        self._id = None

    def _init_table(self):
        self._table = self.define_table()

    def define_table(self):
        raise NotImplementedError('Child model must override define_table()')

    def _init_fields(self):
        fields = self.define_fields()

        if not isinstance(fields, dict):
            fields = {field: None for field in fields}

        for field, default in fields.items():
            setattr(self, field, default)

        self._fields = MappingProxyType(fields)

    def define_fields(self):
        raise NotImplementedError('Child model must override define_fields()')

    def _build_table_if_necessary(self):
        if not self.__class__._table_exists:
            if not self.has_table():
                self.build_table()

            self.__class__._table_exists = True

    def has_table(self):
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

        return int(self.database.fetch_value(query, self.table)) > 0

    def build_table(self):
        with open(inspect.getfile(type(self))[:-3] + '.sql', 'r') as file:
            self.database.execute(file.read(), script=True)

    def _update_table_if_necessary(self):
        if not self.__class__._table_up_to_date:
            if self._needs_new_columns():
                self._update_table()

            self.__class__._table_up_to_date = True

    def _needs_new_columns(self):
        query = """
            pragma table_info('{}')
        """.format(
            self.table
        )

        fields = [f['name'] for f in self.database.fetch_all(query)]
        fields.remove('id')

        return set(fields) != set(self.fields.keys())

    def _update_table(self):
        old_data = self._get_old_data()

        self._delete_table()
        self.build_table()

        for row in old_data:
            fields = dict(self.fields)
            fields.update(row)

            self.database.insert(self.table, fields)

    def _get_old_data(self):
        query = """
            SELECT
                *
            FROM
                {}
            ORDER BY
                id ASC
        """.format(
            self.table
        )

        return self.database.fetch_all(query)

    def _delete_table(self):
        query = """
            DROP TABLE
                {}
        """.format(
            self.table
        )

        self.database.execute(query, commit=False)

    def get_list_by(self, **kwargs):
        if not kwargs:
            return self.get_all()

        all_fields = list(self.fields) + ['id']

        for field in kwargs:
            if field not in all_fields:
                raise AttributeError(
                    'Field "{}" not found in model "{}"'.format(
                        field,
                        type(self).__name__
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
            self.table,
            ' AND '.join('{0} = :{0}'.format(name) for name in kwargs)
        )
        data = self.database.fetch_all(query, kwargs)

        return [self._build_from_fields(fields) for fields in data]

    def _build_from_fields(self, fields):
        fields = dict(fields)

        model = self.__class__(self.bot, self.database)
        model._id = fields.pop('id')
        for field in model.fields:
            value = fields.pop(field)

            if type(getattr(model, field)) is bool:
                value = bool(value)

            setattr(model, field, value)

        if fields:
            logging.warning('{} has extra fields in the database: {!r}'.format(
                type(self).__name__,
                fields
            ))

        return model

    def get_all(self, order_by='id ASC', limit=None):
        query = """
            SELECT
                *
            FROM
                {}
            ORDER BY
                {}
        """.format(self.table, order_by)

        if limit is not None:
            query += 'LIMIT {}'.format(limit)

        data = self.database.fetch_all(query)

        return [self._build_from_fields(fields) for fields in data]

    def get_by(self, **kwargs):
        models = self.get_list_by(**kwargs)
        return models[0] if models else None

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
