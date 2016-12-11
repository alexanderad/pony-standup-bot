import collections
import unittest
from flexmock import flexmock

from pony.jobs import WorldTick


class WorldTickTest(unittest.TestCase):
    def setUp(self):
        queue = collections.deque()
        self.fake_bot = flexmock()
        self.job = WorldTick(self.fake_bot, queue, interval=5)

    def test_init(self):
        self.assertEqual(self.job.interval, 5)
        self.assertIsInstance(self.job.queue, collections.deque)
        self.assertIsNotNone(self.job.bot)

    def test_run(self):
        fake_task = flexmock()
        fake_slack = flexmock()

        (flexmock(fake_task)
         .should_receive('execute')
         .with_args(bot=self.fake_bot, slack=fake_slack)
         .once())

        self.job.queue.append(fake_task)
        self.assertListEqual(self.job.run(fake_slack), list())
        self.assertEqual(len(self.job.queue), 0)
