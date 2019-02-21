import os
import logging
import settings

from datetime import datetime
from .pushbullet_logging import PushbulletHandler


def set_up_logging(pushbullet_token=None):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    add_file_logger(logger, formatter)
    add_console_logger(logger, formatter)
    add_pushbullet_logger(logger, formatter, pushbullet_token)


def add_file_logger(logger, formatter):
    if not settings.log_directory:
        return None

    os.makedirs(settings.log_directory, exist_ok=True)
    filename = '{}/{}.log'.format(
        settings.log_directory,
        datetime.now().strftime('%Y-%m-%d %H-%M-%S')
    )
    filehandler = logging.FileHandler(filename)
    filehandler.setLevel(logging.INFO)
    filehandler.setFormatter(formatter)
    logger.addHandler(filehandler)

    return filehandler


def add_console_logger(logger, formatter):
    streamhandler = logging.StreamHandler()
    streamhandler.setLevel(logging.ERROR)
    streamhandler.setFormatter(formatter)
    logger.addHandler(streamhandler)

    return streamhandler


def add_pushbullet_logger(logger, formatter, pushbullet_token):
    if not pushbullet_token:
        return None

    pushbullethandler = PushbulletHandler(
        access_token=pushbullet_token
    )
    pushbullethandler.setLevel(logging.ERROR)
    pushbullethandler.setFormatter(formatter)
    logger.addHandler(pushbullethandler)

    return pushbullethandler


def remove_pushbullet_logger():
    logger = logging.getLogger()
    logger.handlers = [
        h for h in logger.handlers if not isinstance(h, PushbulletHandler)
    ]
