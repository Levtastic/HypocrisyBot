import asyncio
import aiohttp


async def resolve_redirects(url):
    async with aiohttp.ClientSession() as session:
        print(await _resolve_redirects(url, session))


async def _resolve_redirects(url, session):
    async with session.head(url) as resp:
        if 300 <= resp.status < 400 and 'Location' in resp.headers:
            return await _resolve_redirects(
                resp.headers['Location'],
                session
            )

        return url


asyncio.get_event_loop().run_until_complete(
    resolve_redirects('https://v.redd.it/skpffl4rd5h21')
)
