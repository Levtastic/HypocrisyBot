import re
import asyncio
import aiohttp
import logging
import tempfile

from discord import Embed, NotFound, Forbidden, File
from discord.abc import PrivateChannel
from .models.vreddit_message import VRedditMessage
from .reddit_video import RedditVideo, PostError
from levbot import UserLevel


url_pattern = re.compile(
    r'(?<!<)https?://v\.redd\.it/[^/\s]+/?(?:$|(?=\s))', re.IGNORECASE)


class VReddit:
    def __init__(self, bot):
        self.bot = bot
        self.settings = bot.settings.vreddit
        self.settings.temp_directory = self.settings.temp_directory.format(
            sys_temp=tempfile.gettempdir()
        )

        bot.database.add_models(VRedditMessage)

        bot.register_event('on_ready', self.on_ready)
        bot.register_event('on_message', self.on_message)
        bot.register_event('on_message_edit', self.on_message_edit)
        bot.register_event('on_message_delete', self.on_message_delete)
        bot.register_event('on_reaction_add', self.on_reaction_add)

    async def on_ready(self):
        for message in self.bot.database.VRedditMessage.get_list(
                order_by='id DESC', limit=50):
            try:
                src_message = await message.get_src_message()
                dest_message = await message.get_dest_message()

            except (NotFound, Forbidden):
                src_message = None
                dest_message = None

            if src_message and dest_message:
                self.add_message_to_cache(src_message)
                self.add_message_to_cache(dest_message)

            else:
                message.delete()

        logging.info('old messages fetched')

    def add_message_to_cache(self, message):
        self.bot._connection._messages.append(message)

    async def on_message(self, message):
        await self.handle_new_message(message)

    async def on_message_edit(self, before, after):
        if before.content != after.content:
            # not just an automatic embed change
            await self.handle_new_message(after)

    async def handle_new_message(self, smessage):
        if isinstance(smessage.channel, PrivateChannel):
            return

        url = await self.get_long_url(smessage.content)
        vmessage = self.get_vmessage(smessage)

        if vmessage:
            if url == vmessage.src_url:
                # message looks handled already
                return

            # url changed - delete old embed, start over
            vmessage.delete()

        if not url:
            # no url to handle
            return

        logging.info(f'url "{url}" detected...')

        vmessage = self.bot.database.VRedditMessage()
        vmessage.src_url = url
        vmessage.channel_did = smessage.channel.id
        vmessage.src_message_did = smessage.id
        vmessage.save()

        async with RedditVideo(url, self.settings.temp_directory) as video:
            try:
                await video.populate()
            except PostError:
                logging.info('No video found')
                return vmessage.delete()

            with smessage.channel.typing():
                filename = await video.get_video_file(max_file_size=8)
                if not filename:
                    # no video at this url
                    return vmessage.delete()

                if not vmessage.exists():
                    # check that nothing's changed since we started
                    return

                dmessage = await smessage.channel.send(
                    file=File(
                        filename,
                        filename='reddit.mp4',
                        spoiler=video.spoiler or video.quarantine or video.nsfw
                    ),
                    embed=self.get_embed(
                        smessage,
                        video
                    )
                )

        if vmessage.exists():
            vmessage.dest_message_did = dmessage.id
            vmessage.save()

            await asyncio.gather(
                dmessage.add_reaction('❌'),
                smessage.edit(suppress=True)
            )

        else:
            # dang it, link deleted while we're uploading!
            await dmessage.delete()

    async def get_long_url(self, s):
        url = self.get_url(s)
        if not url:
            return ''

        if 'v.redd.it' in url:
            return await self.resolve_redirects(url)

        return url if url[-1] == '/' else url + '/'

    def get_url(self, s):
        match = url_pattern.search(s)
        return match.group(0) if match else ''

    async def resolve_redirects(self, url):
        async with aiohttp.ClientSession() as session:
            return await self._resolve_redirects(url, session)

    async def _resolve_redirects(self, url, session):
        async with session.head(url) as resp:
            if 300 <= resp.status < 400 and 'Location' in resp.headers:
                return await self._resolve_redirects(
                    resp.headers['Location'],
                    session
                )

            return url

    def get_vmessage(self, smessage, by_source=True):
        if by_source:
            return self.bot.database.VRedditMessage.get_by(
                channel_did=smessage.channel.id,
                src_message_did=smessage.id
            )

        return self.bot.database.VRedditMessage.get_by(
            channel_did=smessage.channel.id,
            dest_message_did=smessage.id
        )

    def get_embed(self, smessage, video):
        description = (
            f'Originally linked by <@{smessage.author.id}>'
        )

        if video.file_size != video.final_file_size:
            percentage = (video.final_file_size / video.file_size) * 100
            description += (
                f'\n\nVideo compressed to {percentage:.2g}% of'
                ' the original file size.'
            )

            if video.is_clipped:
                description += (
                    '\nThis video length may have changed to fit'
                    " Discord's file size limits."
                )

            description += (
                '\nClick the title above to see the original'
                ' quality'
            )
            description += (' and length' if video.is_clipped else '')
            description += ' video on reddit.'

        tags = []
        if video.spoiler:
            tags.append('spoiler')
        if video.quarantine:
            tags.append('quarantine')
        if video.nsfw:
            tags.append('nsfw')

        title = ''
        if tags:
            title = '[{}] '.format(', '.join(tag.upper() for tag in tags))

        title += video.title

        if len(title) > 256:
            title = title[:253] + '...'

        embed = Embed(
            title=title,
            url=video.short_url,
            description=description
        )

        embed.set_footer(text=(
            'Admins and the original poster can click the'
            ' ❌ to delete this message'
        ))

        return embed

    async def on_message_delete(self, smessage):
        if isinstance(smessage.channel, PrivateChannel):
            return

        vmessage = self.get_vmessage(smessage) \
            or self.get_vmessage(smessage, False)

        if vmessage:
            vmessage.delete()

    async def on_reaction_add(self, reaction, user):
        if reaction.emoji != '❌':
            return

        if reaction.message.author != self.bot.user:
            return

        if user == self.bot.user:
            return

        vmessage = self.get_vmessage(reaction.message, False)
        smessage = await vmessage.get_src_message()

        if UserLevel.get(user, reaction.message.channel) \
           >= UserLevel.guild_bot_admin or user == smessage.author:
            vmessage.delete()
            await smessage.edit(suppress=False)
