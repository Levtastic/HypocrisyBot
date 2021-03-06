def wrap(cls, settings):
    cls._ss_message_splitter = MessageSplitter(settings)
    cls._ss_orig_send = cls.send
    cls.send = send


def unwrap(cls):
    cls.send = cls._ss_orig_send
    del cls._ss_orig_send
    del cls._ss_message_splitter


async def send(self, content=None, *args, **kwargs):
    results = []

    for piece in self._ss_message_splitter.split(content):
        results.append(await self._ss_orig_send(piece, *args, **kwargs))

    if len(results) == 1:  # this will usually be the case
        return results[0]

    return results


class MessageSplitter:
    def __init__(self, settings):
        self.max_message_len = settings.max_message_len
        self.newline_search_len = settings.newline_search_len
        self.space_search_len = settings.space_search_len

    def split(self, string):
        if not string:
            return ('',)

        return self.flatten(self.get_pieces(str(string)))

    def get_pieces(self, string):
        if len(string) <= self.max_message_len:
            return (string, )

        piece = string[:self.max_message_len]
        if '\n' in piece[-self.newline_search_len:]:
            piece = piece.rsplit('\n', 1)[0]

        elif ' ' in piece[-self.space_search_len:]:
            piece = piece.rsplit(' ', 1)[0]

        return (piece, self.get_pieces(string[len(piece):]))

    def flatten(self, tpl):
        return tuple(self.flattengen(tpl))

    def flattengen(self, tpl):
        for item in tpl:
            if isinstance(item, tuple):
                yield from self.flattengen(item)

            else:
                yield item
