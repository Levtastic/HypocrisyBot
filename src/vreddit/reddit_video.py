import os
import shutil
import aiohttp
import asyncio
import functools
import logging
import xml.etree.ElementTree as ET

from uuid import uuid1 as uuid


rmtree = functools.partial(shutil.rmtree, ignore_errors=True)


class PostError(Exception):
    pass


class VideoError(Exception):
    pass


class RedditVideo:
    def __init__(self, url, temp_directory, *, loop=None):
        self.url = url
        self.working_dir = os.path.join(temp_directory, str(uuid()))
        self._populated = False

        self.loop = loop or asyncio.get_event_loop()

    async def __aenter__(self):
        os.makedirs(self.working_dir, exist_ok=True)
        self.http_session = await aiohttp.ClientSession().__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs):
        return await asyncio.gather(
            self.loop.run_in_executor(None, rmtree, self.working_dir),
            self.http_session.__aexit__(*args, **kwargs)
        )

    @property
    def is_populated(self):
        return self._populated

    async def get_video_file(self, max_file_size=10485760):
        try:
            await self.populate()
        except PostError:
            logging.info('No video found at ' + self.url)
            return None

        video_file, audio_file = await asyncio.gather(
            self.download_file('v.mp4', self.video_url),
            self.download_file('a.mp4', self.audio_url)
        )

        if audio_file:
            video_file = await self.merge(video_file, audio_file)

        self.file_size = os.path.getsize(video_file)
        self.final_file_size = self.file_size

        if self.file_size > max_file_size:
            video_file = await self.ensure_size(video_file, max_file_size)
            self.final_file_size = os.path.getsize(video_file)

        return video_file

    async def populate(self):
        if self.is_populated:
            return

        async with self.http_session.get(self.url + '.json') as resp:
            data = await resp.json()

        main_data = data[0]['data']['children'][0]['data']

        try:
            video_data = main_data['secure_media']['reddit_video']

            self.title = main_data['title']
            self.short_url = main_data['url']
            self.audio_url = ''  # populate this from the DASH playlist later
            self.video_url = video_data['fallback_url']
            self.height = int(video_data['height'])
            self.width = int(video_data['width'])
            self.duration = int(video_data['duration'])

            self.quarantine = main_data['quarantine']
            self.nsfw = main_data['over_18']
            self.spoiler = main_data['spoiler']

            async with self.http_session.get(video_data['dash_url']) as resp:
                dash_root = ET.fromstring(await resp.text())

            dash_sets = dash_root.iter('{urn:mpeg:dash:schema:mpd:2011}AdaptationSet')

            for dash_set in dash_sets:
                try:
                    if dash_set.attrib['contentType'] == 'audio':
                        self.audio_url = self.short_url + '/' + \
                            next(dash_set.iter('{urn:mpeg:dash:schema:mpd:2011}BaseURL')).text

                except KeyError:
                    if dash_set[0].attrib['mimeType'] == 'audio/mp4':
                        self.audio_url = self.short_url + '/' + \
                            next(dash_set.iter('{urn:mpeg:dash:schema:mpd:2011}BaseURL')).text

        except (KeyError, TypeError):
            logging.exception('Error in RedditVideo.populate')
            raise PostError('Reddit post must contain a video')

        self._populated = True

    async def download_file(self, filename, url, chunk_size=1024):
        if not url:
            return None

        filename = os.path.join(self.working_dir, filename)
        async with self.http_session.get(url) as resp:
            if resp.status != 200:
                return ''

            with open(filename, 'wb') as file:
                while True:
                    chunk = await resp.content.read(chunk_size)
                    if not chunk:
                        return filename

                    file.write(chunk)

    async def merge(self, video_file, audio_file):
        result_file = os.path.join(os.path.dirname(video_file), 'm.mp4')

        cmd = (
            'ffmpeg -hide_banner -loglevel panic'
            f' -i "{video_file}" -i "{audio_file}"'
            ' -c:v copy -c:a copy'
            f' -map 0:v:0 -map 1:a:0 "{result_file}"'
        )

        logging.info('Running command: ' + cmd)

        await self.loop.run_in_executor(None, os.system, cmd)

        return result_file

    async def ensure_size(self, video_file, max_file_size):
        video_file = await self.squish_file(video_file, max_file_size)

        if os.path.getsize(video_file) > max_file_size:
            video_file = await self.clip_file(video_file, max_file_size)

        return video_file

    async def squish_file(self, video_file, max_file_size):
        result_file = os.path.join(os.path.dirname(video_file), 's.mp4')

        max_kbits = max_file_size * 0.008
        ideal_bitrate = max_kbits / self.duration
        ideal_bitrate -= 96  # audio channel
        ideal_bitrate *= 0.98  # allow room for metadata

        if ideal_bitrate < 5:
            # ahahahaha no
            ideal_bitrate = 5

        rescale = ''
        if self.height > 480:
            rescale = '-vf scale="trunc(oh*a/2)*2:480"'

        cmd = (
            'ffmpeg -hide_banner -loglevel panic'
            f' -y -i "{video_file}"'
            f' -c:v libx264 -b:v {ideal_bitrate}k -pass 1 -an'
            f' {rescale}'
            f' -f mp4 {os.devnull} &&'
            ' ffmpeg -hide_banner -loglevel panic'
            f' -i "{video_file}"'
            f' -c:v libx264 -b:v {ideal_bitrate}k -pass 2'
            f' {rescale}'
            ' -c:a aac -b:a 96k -strict -2'
            f' "{result_file}"'
        )

        logging.info('Running command: ' + cmd)

        await self.loop.run_in_executor(None, os.system, cmd)

        return result_file

    async def clip_file(self, video_file, max_file_size):
        result_file = os.path.join(os.path.dirname(video_file), 'c.mp4')

        max_file_size -= 10000  # space for final closing bytes

        cmd = (
            'ffmpeg -hide_banner -loglevel panic'
            f' -i "{video_file}"'
            f' -c copy -fs {max_file_size}'
            f' "{result_file}"'
        )

        logging.info('Running command: ' + cmd)

        await self.loop.run_in_executor(None, os.system, cmd)

        return result_file
