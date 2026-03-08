import asyncio
import logging
from typing import Callable, Coroutine, Dict

logger = logging.getLogger("EH_Queue")

class EngineQueueStore:
    def __init__(self):
        self.channel_queues: Dict[int, asyncio.Queue] = {}
        self.channel_workers: Dict[int, asyncio.Task] = {}
        self.mutation_queue = asyncio.Queue()
        self.mutation_worker: asyncio.Task = None
        self._shutdown = False

    def get_channel_queue(self, channel_id: int) -> asyncio.Queue:
        if channel_id not in self.channel_queues:
            self.channel_queues[channel_id] = asyncio.Queue()
            self.channel_workers[channel_id] = asyncio.create_task(
                self._channel_worker_loop(channel_id), 
                name=f"Worker-Channel-{channel_id}"
            )
        return self.channel_queues[channel_id]

    async def _channel_worker_loop(self, channel_id: int):
        queue = self.channel_queues[channel_id]
        while True:
            try:
                task = await queue.get()
                if task is None: # Sentinel for shutdown
                    queue.task_done()
                    break
                coro, args, kwargs = task
                try:
                    await coro(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error executing narrative task in channel {channel_id}: {e}", exc_info=True)
                finally:
                    queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in channel {channel_id} worker loop: {e}", exc_info=True)

    def start_mutation_worker(self):
        if self.mutation_worker is None or self.mutation_worker.done():
            self.mutation_worker = asyncio.create_task(
                self._mutation_worker_loop(), 
                name="Worker-Mutation"
            )

    async def _mutation_worker_loop(self):
        while True:
            try:
                task = await self.mutation_queue.get()
                if task is None:
                    self.mutation_queue.task_done()
                    break
                coro, args, kwargs = task
                try:
                    await coro(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error executing mutation task: {e}", exc_info=True)
                finally:
                    self.mutation_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in mutation worker loop: {e}", exc_info=True)

    async def enqueue_narrative(self, channel_id: int, coro_fn: Callable[..., Coroutine], *args, **kwargs):
        """Enqueue an AI generation or narrative action for a specific channel."""
        if self._shutdown:
            logger.warning("Queues are shutting down. Cannot enqueue.")
            return
        q = self.get_channel_queue(channel_id)
        await q.put((coro_fn, args, kwargs))

    async def enqueue_mutation(self, coro_fn: Callable[..., Coroutine], *args, **kwargs):
        """Enqueue state mutation tasks isolated from channels."""
        if self._shutdown:
            logger.warning("Queues are shutting down. Cannot enqueue.")
            return
        self.start_mutation_worker()
        await self.mutation_queue.put((coro_fn, args, kwargs))

    async def graceful_shutdown(self):
        self._shutdown = True
        logger.info("Initiating graceful shutdown of Engine Queues...")

        # Enqueue sentinels
        if self.mutation_worker and not self.mutation_worker.done():
            await self.mutation_queue.put(None)

        for q in self.channel_queues.values():
            await q.put(None)

        # Gather tasks and wait for queues to empty
        tasks = []
        if self.mutation_worker and not self.mutation_worker.done():
             tasks.append(self.mutation_worker)
        tasks.extend(self.channel_workers.values())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Engine Queues drained and shut down.")

    def restart(self):
        """Reset queue state after a hot-reload so new enqueues are accepted."""
        self._shutdown = False
        self.channel_queues.clear()
        self.channel_workers.clear()
        self.mutation_queue = asyncio.Queue()
        self.mutation_worker = None
        logger.info("Engine Queues restarted.")

# Singleton instance
engine_queues = EngineQueueStore()
