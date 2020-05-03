import re
import asyncio
import aiohttp
import logging

from discord import Embed, NotFound, Forbidden, File
from discord.abc import PrivateChannel
from .models.vreddit_message import VRedditMessage
from .reddit_video import RedditVideo, PostError
from levbot import UserLevel


url_chars = r'[a-z0-9\._~%\-\+&\#\?!=\(\)@]'
url_pattern = re.compile(r'(?<!<)https?://(?:(?:\S*\.)?reddit\.com/r/' +
                         url_chars + r'+/comments/' + url_chars +
                         r'+/' + url_chars + r'+/?|v\.redd\.it/' +
                         url_chars + r'+/?)\b',
                         re.IGNORECASE)


class VReddit:
    def __init__(self, bot, temp_directory):
        self.bot = bot
        self.temp_directory = temp_directory

        bot.database.add_models(VRedditMessage)

        bot.register_event('on_ready', self.on_ready)
        bot.register_event('on_message', self.on_message)
        bot.register_event('on_message_edit', self.on_message_edit)
        bot.register_event('on_message_delete', self.on_message_delete)
        bot.register_event('on_reaction_add', self.on_reaction_add)

    async def on_ready(self):
        for message in self.bot.database.get_VRedditMessage_list(
                order_by='id DESC', limit=50):
            try:
                src_message = await message.get_src_message()
                dest_message = await message.get_dest_message()

            except (NotFound, Forbidden):
                src_message = None
                dest_message = None

            if src_message and dest_message:
                self.bot.messages.append(src_message)
                self.bot.messages.append(dest_message)

            else:
                message.delete()

        logging.info('old messages fetched')

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

        vmessage = self.bot.database.get_VRedditMessage()
        vmessage.src_url = url
        vmessage.channel_did = smessage.channel.id
        vmessage.src_message_did = smessage.id
        vmessage.save()

        async with RedditVideo(url, self.temp_directory) as video:
            try:
                await video.populate()
            except PostError:
                logging.info('No video found')
                return vmessage.delete()

            with smessage.channel.typing():
                filename = await video.get_video_file(
                    max_file_size=7.75 * 1024 * 1024)
                if not filename:
                    # no video at this url
                    return vmessage.delete()

                if not vmessage.exists():
                    # check that nothing's changed since we started
                    return

                dmessage = await smessage.channel.send(
                    file=File(
                        filename,
                        filename='reddit.mp4'
                    ),
                    embed=self.get_embed(
                        smessage,
                        video
                    )
                )

        if vmessage.exists():
            vmessage.dest_message_did = dmessage.id
            vmessage.save()

            await dmessage.add_reaction('❌')

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
            return self.bot.database.get_VRedditMessage().get_by(
                channel_did=smessage.channel.id,
                src_message_did=smessage.id
            )

        return self.bot.database.get_VRedditMessage().get_by(
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
                '\nClick the title above to see the original'
                ' quality video on reddit'
            )

        embed = Embed(
            title=video.title,
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

        if UserLevel.get(user, reaction.message.channel) \
           >= UserLevel.guild_bot_admin:
            vmessage.delete()
            return

        smessage = await vmessage.get_src_message()

        if user == smessage.author:
            vmessage.delete()
            return
