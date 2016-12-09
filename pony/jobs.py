# coding=utf-8
import time

from rtmbot.core import Job


class WorldTick(Job):
    """World tick."""
    def __init__(self, bot, queue, interval):
        super(WorldTick, self).__init__(interval)
        self.bot = bot
        self.queue = queue

    def run(self, slack):
        visible_tasks = len(self.queue)

        for x in range(visible_tasks):
            task = self.queue.popleft()
            task.execute(bot=self.bot, slack=slack)
            time.sleep(0.25)

        return []
