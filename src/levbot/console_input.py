import sys
import traceback
import asyncio

from concurrent.futures import thread, CancelledError


class ConsoleInput:
    def __init__(self, bot, local_vars={}):
        self.bot = bot
        self.locals = local_vars

        self.is_ready = asyncio.Event()
        self.commands = (
            'exit',
        )

        WriterWrapper(sys.stdout, self.is_ready)
        WriterWrapper(sys.stderr, self.is_ready)
        self.disable_daemon_thread_exit()
        self.bot.loop.create_task(self.loop())

    @staticmethod
    def disable_daemon_thread_exit():
        import atexit
        import concurrent.futures

        def _python_exit():
            concurrent.futures.thread._shutdown = True
            items = list(thread._threads_queues.items())
            for t, q in items:
                q.put(None)
            for t, q in items:
                if not t.daemon:
                    t.join()

        atexit.unregister(thread._python_exit)
        atexit.register(_python_exit)

    async def loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(0)

        self.is_ready.set()

        while not self.bot.is_closed():
            await self.is_ready.wait()
            message = await self.get_console_input()

            if message == 'exit':
                self.is_ready.clear()
                print('Shutting down!')
                await self.bot.close()
                return

            try:
                exec(
                    'async def f(' + ','.join(self.locals.keys()) + '):\n' +
                    ' {}\n'.format('\n '.join(
                        line for line in message.split('\n'))
                    ) +
                    'fut = asyncio.ensure_future(f(**self.locals))\n' +
                    'fut.add_done_callback(self.on_complete)\n'
                )

                self.is_ready.clear()
                print('Executing code...')

            except (KeyboardInterrupt, SystemExit, GeneratorExit,
                    CancelledError):
                raise

            except BaseException:
                self.is_ready.set()
                traceback.print_exc(file=sys.stdout)

    async def get_console_input(self):
        lines = []

        while not self.bot.is_closed():
            line = await self.bot.loop.run_in_executor(None, input, "\r> ")

            command = line.lower()

            if not lines and command in self.commands:
                return command

            if line:
                lines.append(line)

            elif lines:
                return '\n'.join(lines)

    def on_complete(self, fut):
        self.is_ready.set()

        try:
            print('Code completed - result: ' + repr(fut.result()))

        except (KeyboardInterrupt, SystemExit, GeneratorExit, CancelledError):
            raise

        except BaseException:
            traceback.print_exc(file=sys.stdout)


class WriterWrapper:
    def __init__(self, writer, console_ready):
        self.console_ready = console_ready
        self.old_write = writer.write

        self.start_of_line = True

        writer.write = lambda s: self.write_wrap(s)

    def write_wrap(self, s):
        if not self.console_ready.is_set():
            self.start_of_line = True
            return self.old_write(s)

        if self.start_of_line:
            s = "\r" + s
            self.start_of_line = False

        if s.endswith("\n"):
            s += '> '
            self.start_of_line = True

        return self.old_write(s)
