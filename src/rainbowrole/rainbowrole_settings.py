from levbot import settings


def get_category():
    return ('rainbowrole', RainbowRoleSettings())


class RainbowRoleSettings(settings.Category):
    guild_id = ''
    role_id = ''
