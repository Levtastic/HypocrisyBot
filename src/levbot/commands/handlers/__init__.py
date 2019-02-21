import os as _os
from importlib import import_module as _import


_dir = _os.path.dirname(_os.path.realpath(__file__))
_globals = globals()
for _file in _os.listdir(_dir):
    if not _os.path.isfile(_os.path.join(_dir, _file)):
        continue

    if _file[0] == '_':
        continue

    _module_name = _os.path.splitext(_file)[0]
    _class_name = ''.join(word.title() for word in _module_name.split('_'))

    _module = _import('.' + _module_name, __name__)
    _globals[_class_name] = getattr(_module, _class_name)
