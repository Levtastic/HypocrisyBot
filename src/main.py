import sys
import logging

from levbot import Bot
from levbot.settings import Loader
from vreddit import VReddit, vreddit_settings
from rainbowrole import RainbowRole, rainbowrole_settings
from reactionrole import ReactionRole
from userannounce import UserAnnounce, userannounce_settings
from servericonswitcher import ServerIconSwitcher, servericonswitcher_settings


def get_bot():
    settings = get_settings()

    bot = Bot(settings)

    @bot.event()
    async def on_ready():
        print(f'Connected as {bot.user}')

    VReddit(bot)
    RainbowRole(bot)
    ReactionRole(bot)
    UserAnnounce(bot)
    ServerIconSwitcher(bot)

    return bot


def get_settings():
    loader = Loader('settings.toml')
    loader.add_category(*vreddit_settings.get_category())
    loader.add_category(*rainbowrole_settings.get_category())
    loader.add_category(*userannounce_settings.get_category())
    loader.add_category(*servericonswitcher_settings.get_category())
    return loader.load()


if __name__ == '__main__':
    bot = get_bot()

    if '--update-tables' in sys.argv:
        for handler in bot.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(logging.INFO)

        bot.database.force_update_model_tables()

    else:
        bot.run()


# https://discordapi.com/permissions.html#499248208
