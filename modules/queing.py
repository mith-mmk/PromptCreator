import asyncio

from modules.logger import getDefaultLogger

Logger = getDefaultLogger()


class BackgroundWorker:
    def __init__(self, max_tasks=3):
        self._queue = asyncio.Queue()
        self._tasks = []
        self._result = {}
        self.max_tasks = max_tasks
        asyncio.create_task(self.worker())

    async def worker(self):
        Logger.info("BackgroundWorker start")
        while True:
            while self._queue.empty():
                await asyncio.sleep(0.01)
            (work, id) = await self._queue.get()
            self._result[id] = None
            if work[0] == "done":
                Logger.info("BackgroundWorker end")
                return
            if work[0] == "save":
                import modules.save as save

                save.save_img(work[1], work[2])

    def put(self, work):
        self._tasks.append(work)
        id = len(self._tasks) - 1
        asyncio.create_task(self._queue.put((work, id)))
        return id

    async def done(self):
        await self.put(("done", None))
        await self._queue.join()

    def get(self, task_id):
        return self._result[task_id]
