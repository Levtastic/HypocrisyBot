from .models.reaction_role import ReactionRole as ReactionRoleModel


class ReactionRole:
    def __init__(self, bot):
        self.bot = bot

        bot.database.add_models(ReactionRoleModel)

        bot.register_event('on_raw_reaction_add', self.on_raw_reaction_add)
        bot.register_event('on_raw_reaction_remove',
                           self.on_raw_reaction_remove)

    async def on_raw_reaction_add(self, event):
        reactionrole = self.get_reactionrole(event)

        if not reactionrole:
            return

        member = reactionrole.guild.get_member(event.user_id)

        if reactionrole.role in member.roles:
            return

        await member.add_roles(reactionrole.role,
                               reason='User reacted for role')

    def get_reactionrole(self, event):
        return self.bot.database.ReactionRole.get_by(
            message_did=event.message_id,
            emoji=event.emoji.id or event.emoji.name
        )

    async def on_raw_reaction_remove(self, event):
        reactionrole = self.get_reactionrole(event)

        if not reactionrole:
            return

        member = reactionrole.guild.get_member(event.user_id)

        if reactionrole.role not in member.roles:
            return

        await member.remove_roles(reactionrole.role,
                                  reason='User unreacted for role')
