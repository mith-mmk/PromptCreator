import asyncio
import logger as Logger


class BackgroundWorker:
    def __init__(self, max_tasks=3):
        self._queue = asyncio.Queue()
        self._woker_queue = asyncio.Queue()
        self._result_queue = asyncio.Queue()
        self._tasks = []
        self.max_tasks = max_tasks

    def new_woker_start(self):
        asyncio.run(self.main())

    def woker_cancel(self):
        self._queue.put_nowait('done')
        for task in self._tasks:
            task.cancel()
        asyncio.run(asyncio.gather(*self._tasks, return_exceptions=True))
        self._tasks = []

    async def main(self):
        # woker start up
        for i in range(self.max_tasks):
            task = asyncio.create_task(self.worker(f'worker-{i}', self.woker_queue, self.result_queue))
            self._tasks.append(task)
        # work
        while True:
            work = await self._queue.get()
            if type(work) == str:
                work = work.split()
            if work[0] == 'done':
                for i in range(self.max_tasks):
                    await self.woker_queue.put('done')
                self._queue.task_done()
                break
            await self.woker_queue.put(work)
            self._queue.task_done()

    async def put(self, work):
        await self._queue.put(work)

    async def get(self):
        return await self._result_queue.get()

    async def worker(self, name, worker_queue, result_queue):
        Logger.debug(f'worker {name} start')
        while True:
            # Get a "work item" out of the queue.
            work = await worker_queue.get()
            match work[0]:
                case 'clone':
                    # fileclone(src, dst)
                    result_queue.put_nowait(f'result: {name} clone {work[1]} {work[2]}')
                case 'save':
                    # savefile(filename, data, options)
                    result_queue.put_nowait(f'result: {name} save {work[1]} {work[2]}')
                case 'custom':
                    # customfunc(*work[1:])
                    result_queue.put_nowait(f'result: {name} custom {work[1:]}')
                case 'done':
                    result_queue.put_nowait(f'result: {name} done')
                    break
            Logger.debug(f'worker {name} {work} end')
            worker_queue.task_done()
        Logger.debug(f'worker {name} end')
