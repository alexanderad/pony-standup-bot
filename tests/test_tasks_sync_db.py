from __future__ import absolute_import

from flexmock import flexmock

import pony.tasks
from tests.test_base import BaseTest


class SyncDBTest(BaseTest):
    def test_execute(self):
        task = pony.tasks.SyncDB()

        (flexmock(self.bot.storage)
         .should_receive('save')
         .once())

        task.execute(self.bot)
        self.assertIsInstance(self.bot.slow_queue.pop(), pony.tasks.SyncDB)
