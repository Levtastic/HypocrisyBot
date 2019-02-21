import asyncio


bot = None


class TypingContext:
    def __init__(self, channel, delay_between=5, loop=None):
        if not bot:
            raise RuntimeError('Bot not yet initialised when'
                               ' TypingContext created')

        self.channel = channel
        self.delay_between = delay_between
        self.loop = loop or asyncio.get_event_loop()
        self.typing = False

    def __enter__(self):
        self.typing = True
        self.loop.create_task(self.send_typing())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.typing = False

    async def send_typing(self):
        while self.typing:
            await asyncio.gather(
                bot.send_typing(self.channel),
                asyncio.sleep(self.delay_between, loop=self.loop)
            )
