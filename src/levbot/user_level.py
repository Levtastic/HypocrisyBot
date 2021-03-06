import discord

from discord import DMChannel
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
            db_user = database.User.get_by(user_did=user.id)

        if db_user and db_user.blacklisted:
            return cls.blacklisted

        if db_user and db_user.global_admin:
            return cls.global_bot_admin

        if isinstance(channel_or_guild, discord.Guild):
            guild = channel_or_guild
            return _get_max_userlevel(user, guild, db_user)

        channel = channel_or_guild

        if channel and isinstance(channel, PrivateChannel):
            return cls._get_private_level(user, channel)

        return cls._get_guild_level(user, channel, db_user)

    @classmethod
    def _get_max_userlevel(cls, user, guild, db_user):
        max_userlevel = cls.blacklisted

        for channel in guild.channels:
            userlevel = _get_guild_level(user, channel, db_user)
            if userlevel > max_userlevel:
                max_userlevel = userlevel

        return max_userlevel

    @classmethod
    def _get_private_level(cls, user, channel):
        if isinstance(channel, DMChannel):
            if user == channel.recipient:
                return cls.guild_admin
            else:
                return cls.no_access

        if user not in channel.recipients:
            return cls.no_access

        if user != channel.owner:
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
