import sys
import logging
import settings

from levbot import Bot
from vreddit.vreddit import VReddit
from face_avatars.face_avatars import FaceAvatars


def get_bot():
    dsettings = {v: getattr(settings, v) for v in dir(settings) if v[0] != '_'}

    bot = Bot(dsettings)

    @bot.event()
    async def on_ready():
        print(f'Connected as {bot.user}')

    VReddit(bot, dsettings['temp_directory'])
    FaceAvatars(bot, dsettings['avatar_generator_url'])

    return bot


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
# https://github.com/daboth/pagan/blob/master/README.md
