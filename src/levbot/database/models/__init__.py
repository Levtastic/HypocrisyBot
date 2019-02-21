import os as _os
from importlib import import_module as _import

from .model import Model


_dir = _os.path.dirname(_os.path.realpath(__file__))
_globals = globals()
for _folder in _os.listdir(_dir):
    if _os.path.isfile(_os.path.join(_dir, _folder)):
        continue

    if _folder[0] == '_':
        continue

    _module_name = _os.path.splitext(_folder)[0]
    _class_name = ''.join(word.title() for word in _module_name.split('_'))

    _import('.' + _module_name, __name__)
    _module = _import('.' + _module_name, __name__ + '.' + _module_name)
    _globals[_class_name] = getattr(_module, _class_name)
