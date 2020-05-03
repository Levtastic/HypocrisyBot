import discord

from discord import ChannelType
from discord.abc import PrivateChannel
from .ordered_enum import OrderedEnum


owner_usernames = []
database = None


class UserLevel(OrderedEnum):
    bot_owner         = 7
    global_bot_admin  = 6
    guild_owner       = 5
    guild_admin       = 4
    guild_bot_admin   = 3
    guild_user        = 2
    user              = 1
    no_access         = 0
    guild_blacklisted = -1
    blacklisted       = -2

    def __bool__(self):
        return self.value > 0

    @classmethod
    def get(cls, user, channel_or_guild):
        if str(user) in owner_usernames:
            return cls.bot_owner

        db_user = None

        if database:
            db_user = database.get_User_by_user_did(user.id)

        if db_user and db_user.blacklisted:
            return cls.blacklisted

        if db_user and db_user.global_admin:
            return cls.global_bot_admin

        if isinstance(channel_or_guild, discord.Guild):
            channel = channel_or_guild.default_channel
        else:
            channel = channel_or_guild

        if channel and isinstance(channel, PrivateChannel):
            return cls._get_private_level(user, channel)

        return cls._get_guild_level(user, channel, db_user)

    @classmethod
    def _get_private_level(cls, user, channel):
        if user not in channel.recipients:
            return cls.no_access

        if channel.type == ChannelType.group and user != channel.owner:
            return cls.user

        return cls.guild_admin

    @classmethod
    def _get_guild_level(cls, user, channel, db_user):
        member = channel.guild.get_member(user.id)

        if not member:
            return cls.no_access

        if channel and member == channel.guild.owner:
            return cls.guild_owner

        if db_user and db_user.is_blacklisted(channel.guild):
            return cls.guild_blacklisted

        if channel and channel.permissions_for(member).manage_channels:
            return cls.guild_admin

        if channel and db_user and db_user.is_admin(channel.guild):
            return cls.guild_bot_admin

        return cls.guild_user
