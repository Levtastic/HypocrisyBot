from levbot import settings


def get_category():
    return ('userannounce', UserAnnounceSettings())


class UserAnnounceSettings(settings.Category):
    channel_id = ''
