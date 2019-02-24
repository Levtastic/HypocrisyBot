import settings

from levbot import Bot
from vreddit.vreddit import VReddit
from face_avatars.face_avatars import FaceAvatars


settings = {v: getattr(settings, v) for v in dir(settings) if v[0] != '_'}

bot = Bot(settings)


@bot.event()
async def on_ready():
    print(f'Connected as {bot.user}')


VReddit(bot, settings['temp_directory'])
FaceAvatars(bot, 'https://thiscatdoesnotexist.com/')

bot.run()

# https://discordapi.com/permissions.html#499248208
# https://github.com/daboth/pagan/blob/master/README.md
