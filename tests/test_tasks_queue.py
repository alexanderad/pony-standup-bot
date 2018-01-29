from __future__ import absolute_import

import unittest
from flexmock import flexmock
from freezegun import freeze_time

from pony.tasks_queue import TasksQueue


class TasksQueueTest(unittest.TestCase):
    def setUp(self):
        self.bot = flexmock(debug=False, log=flexmock())
        self.queue = TasksQueue(self.bot, 1)

    def test_size(self):
        self.assertEqual(self.queue.size, 0)

    def test_append(self):
        self.queue.append(flexmock())
        self.assertEqual(self.queue.size, 1)

    def test_process_time_to_run(self):
        with freeze_time():
            task = flexmock()
            self.queue = TasksQueue(self.bot, 1)
            self.queue.append(task)

            (flexmock(task)
             .should_receive('execute')
             .times(0))

            self.assertEqual(self.queue.process(), 0)

    def test_process(self):
        with freeze_time() as frozen_time:
            task = flexmock()
            self.queue = TasksQueue(self.bot, 0.5)
            self.queue.append(task)

            frozen_time.tick()

            (flexmock(task)
             .should_receive('execute')
             .with_args(self.bot)
             .and_return(True)
             .times(1))

            self.assertEqual(self.queue.process(), 1)

    def test_when_process_raises_exception_and_debug_is_false(self):
        with freeze_time() as frozen_time:
            task = flexmock()
            self.queue = TasksQueue(self.bot, 0.5)
            self.queue.append(task)

            frozen_time.tick()

            (flexmock(task)
             .should_receive('execute')
             .and_raise(IndexError)
             .times(1))

            (flexmock(self.bot.log)
             .should_receive('error')
             .with_args(str)
             .times(1))

            self.assertEqual(self.queue.process(), 1)
            self.assertEqual(self.queue.process(), 0)
