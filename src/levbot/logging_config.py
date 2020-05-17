import os
import logging

from datetime import datetime
from .pushbullet_logging import PushbulletHandler
from .settings import SettingsKeyError


def set_up_logging(settings):
    logger = logging.getLogger()
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_level, console_level, pushbullet_level = get_log_levels(settings)
    logger.setLevel(min(file_level, console_level, pushbullet_level))

    add_file_logger(logger, formatter, settings, file_level)
    add_console_logger(logger, formatter, console_level)
    add_pushbullet_logger(logger, formatter, settings, pushbullet_level)


def get_log_levels(settings):
    file_level = get_log_level(settings.levels.file)
    console_level = get_log_level(settings.levels.console)
    pushbullet_level = get_log_level(settings.levels.pushbullet)
    return file_level, console_level, pushbullet_level


def get_log_level(setting):
    if setting.upper() not in ('CRITICAL', 'ERROR', 'WARNING',
                               'INFO', 'DEBUG', 'NOTSET'):
        raise SettingsKeyError(f'Log level `{setting}` not recognised.')

    return getattr(logging, setting.upper())


def add_file_logger(logger, formatter, settings, log_level):
    if not settings.directory:
        return None

    os.makedirs(settings.directory, exist_ok=True)
    filename = '{}/{}.log'.format(
        settings.directory,
        datetime.now().strftime('%Y-%m-%d %H-%M-%S')
    )
    filehandler = logging.FileHandler(filename)
    filehandler.setLevel(log_level)
    filehandler.setFormatter(formatter)
    logger.addHandler(filehandler)

    return filehandler


def add_console_logger(logger, formatter, log_level):
    streamhandler = logging.StreamHandler()
    streamhandler.setLevel(log_level)
    streamhandler.setFormatter(formatter)
    logger.addHandler(streamhandler)

    return streamhandler


def add_pushbullet_logger(logger, formatter, settings, log_level):
    if not settings.pushbullet_token:
        return None

    pushbullethandler = PushbulletHandler(
        access_token=settings.pushbullet_token
    )
    pushbullethandler.setLevel(log_level)
    pushbullethandler.setFormatter(formatter)
    logger.addHandler(pushbullethandler)

    return pushbullethandler


def remove_pushbullet_logger():
    logger = logging.getLogger()
    logger.handlers = [
        h for h in logger.handlers if not isinstance(h, PushbulletHandler)
    ]
