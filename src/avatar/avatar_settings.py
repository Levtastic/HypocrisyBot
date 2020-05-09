from levbot import settings


def get_category():
    return ('avatar_generator', AvatarCategory())


class AvatarCategory(settings.Category):
    url = ''
