import abc
import logging
import toml

from dataclasses import dataclass
from types import MappingProxyType


__all__ = ['Loader', 'Category', 'Required',
           'SettingsKeyError', 'SettingsTypeError']


class Loader:
    def __init__(self, filename):
        self.filename = filename
        self._categories = {'bot': BotCategory()}
        self.categories = MappingProxyType(self._categories)
        self._errors = []

    def add_category(self, name, category):
        if name in self._categories:
            raise SettingsKeyError(f'Defaults for category `{key}`'
                                    ' provided more than once.')

        if not (category and isinstance(category, Category)):
            raise SettingsTypeError(f'Incorrect Category type for `{key}:'
                                    f' `{type(category)}`')

        self._categories[name] = category

    def remove_category(self, name):
        return self._categories.pop(name, None) is not None

    def load(self):
        self._errors.clear()
        toml_dict = toml.load(self.filename)

        for name, category in self.categories.items():
            self._load_category(category, name, toml_dict)

        if self._errors:
            raise SettingsError(self._errors)

        if self._has_leftover_values(toml_dict):
            logging.warning(f'Leftover settings remain: `{repr(toml_dict)}`')

        return Settings(self.categories)

    def _load_category(self, category, name, toml_dict, _prefix=''):
        settings = [s for s in dir(category) if not s.startswith('__')]
        for setting in settings:
            try:
                self._load_setting(setting, category, name, toml_dict, _prefix)
            except SettingsError as ex:
                self._errors.append(ex)

    def _load_setting(self, setting, category, name, toml_dict, prefix):
        default = getattr(category, setting)
        setting_type = type(default)
        required = False

        if isinstance(default, Required):
            setting_type = default.type
            required = True

        category_dict = toml_dict.get(name, {})

        if not isinstance(category_dict, dict):
            raise SettingsTypeError(f'Setting `{name}` must be a category'
                                    f' but was `{type(category_dict)}'
                                     ' instead.`')

        if isinstance(default, Category):
            return self._load_category(default, setting, category_dict,
                                       f'{name}.{prefix}')

        if setting in category_dict:
            # remove (pop) from dict so we know it was used
            value = category_dict.pop(setting)
            value_type = type(value)

            if value_type is not setting_type:
                raise SettingsTypeError(f'Setting `{prefix}{name}:{setting}`'
                                        f' must be of type `{setting_type}`'
                                        f' but was `{value_type}` instead.')

            setattr(category, setting, value)

        elif required:
            raise SettingsKeyError(f'Setting `{prefix}{name}:{setting}`'
                                    ' required but not provided.')

    def _has_leftover_values(self, toml_dict):
        has_leftovers = False

        # copy to list since dict changes size while iterating
        for key, value in list(toml_dict.items()):
            if not isinstance(value, dict):
                has_leftovers = True
                continue

            if self._has_leftover_values(value):
                has_leftovers = True
            else:
                del toml_dict[key]  # remove empty subdicts

        return has_leftovers


class Settings:
    def __init__(self, categories):
        for name, category in categories.items():
            setattr(self, name, category)


class Category(abc.ABC):
    pass


@dataclass
class Required:
    type: type


class BotMainCategory(Category):
    token = Required(str)
    db_name = 'levbot.db'
    owner_usernames = []
    offer_invite_link = False
    source_url = ''
    donate_url = ''


class BotLogLevelsCategory(Category):
    file = 'INFO'
    console = 'ERROR'
    pushbullet = 'ERROR'


class BotLogsCategory(Category):
    directory = ''
    pushbullet_token = ''
    levels = BotLogLevelsCategory()


class BotAvatarCategory(Category):
    url = ''
    refresh_command = ''
    random_change_min = 0
    random_change_max = 0


class BotCategory(Category):
    main = BotMainCategory()
    logs = BotLogsCategory()
    avatar = BotAvatarCategory()


class SettingsError(Exception):
    pass


class SettingsKeyError(KeyError, SettingsError):
    pass


class SettingsTypeError(TypeError, SettingsError):
    pass
