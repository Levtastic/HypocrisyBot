def wrap(cls, max_message_len=2000, newline_search_len=200,
         space_search_len=100):
    cls._ss_orig_send = cls.send
    cls.send = send
    cls._ss_max_message_len = max_message_len
    cls._ss_newline_search_len = newline_search_len
    cls._ss_space_search_len = space_search_len
    cls._ss_split_message = _ss_split_message
    cls._ss_get_split_pieces = _ss_get_split_pieces


def unwrap(cls):
    cls.send = cls._ss_orig_send
    del(_ss_max_message_len)
    del(_ss_newline_search_len)
    del(_ss_space_search_len)
    del(cls._ss_orig_send)
    del(cls._ss_split_message)
    del(cls._ss_get_split_pieces)


async def send(self, content=None, *args, **kwargs):
    if content and len(str(content)) > self._ss_max_message_len:
        return await self._ss_split_message(
            str(content), *args, **kwargs
        )

    return await self._ss_orig_send(content, *args, **kwargs)


async def _ss_split_message(self, content, *args, **kwargs):
    clipped, remainder = self._ss_get_split_pieces(content)

    message1 = await self._ss_orig_send(clipped, *args, **kwargs)
    message2 = await self._ss_orig_send(remainder, *args, **kwargs)

    if not isinstance(message2, tuple):
        message2 = (message2, )

    return (message1, *message2)


def _ss_get_split_pieces(self, string):
    piece = string[:self._ss_max_message_len]
    if '\n' in piece[-self._ss_newline_search_len:]:
        piece = piece.rsplit('\n', 1)[0]

    elif ' ' in piece[-self._ss_space_search_len:]:
        piece = piece.rsplit(' ', 1)[0]

    return piece, string[len(piece):]
