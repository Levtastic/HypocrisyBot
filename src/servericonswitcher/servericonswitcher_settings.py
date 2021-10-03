from levbot import settings


def get_category():
    return ('servericonswitcher', ServerIconSwitcherSettings())


class ServerIconSwitcherSettings(settings.Category):
    guild_id = ''
    image_1 = ''
    image_2 = ''
    image_3 = ''
    between_switches = [300, 1200]  # 5 to 20 minutes
    switch_length = [1, 5]
    image_2_chance = 90
