from levbot import settings


def get_category():
    return ('vreddit', VRedditCategory())


class VRedditCategory(settings.Category):
    temp_directory = '{sys_temp}/vreddit'
