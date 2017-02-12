from __future__ import absolute_import

from datetime import date, datetime

import freezegun
from flexmock import flexmock

import pony.tasks
from pony.dictionary import Dictionary
from tests.test_base import BaseTest


class AskStatusTest(BaseTest):
    def setUp(self):
        super(AskStatusTest, self).setUp()
        self.bot.plugin_config = {}
        self.bot.storage.set('report', {
            date.today(): {
                't1': {
                    'reports': {
                        'U023BECGF': {
                            'report': []
                        }
                    }
                },
                't2': {
                    'reports': {
                        'U023BECGF': {
                            'report': []
                        }
                    }
                }
            }
        })
        # by default assume user is online
        (flexmock(self.bot)
         .should_receive('user_is_online')
         .with_args('U023BECGF')
         .and_return(True))

    def test_execute_user_already_locked(self):
        self.bot.lock_user('U023BECGF', ['t1', 't2'], 10)
        task = pony.tasks.AskStatus(['t1', 't2'], 'U023BECGF', last_call=False)
        task.execute(self.bot, self.slack)

        with self.assertRaises(IndexError):
            self.bot.fast_queue.pop()

    def test_execute_user_is_offline(self):
        (flexmock(self.bot)
         .should_receive('user_is_online')
         .with_args('U023BECGF')
         .and_return(False))

        task = pony.tasks.AskStatus(['t1', 't2'], 'U023BECGF', last_call=False)
        task.execute(self.bot, self.slack)

        with self.assertRaises(IndexError):
            self.bot.fast_queue.pop()

    def test_execute_sets_user_lock(self):
        task = pony.tasks.AskStatus(['t1', 't2'], 'U023BECGF', last_call=False)
        task.execute(self.bot, self.slack)

        self.assertListEqual(self.bot.get_user_lock('U023BECGF'), ['t1', 't2'])

    def test_execute_lock_does_blocks_duplicate_inquiries(self):
        task = pony.tasks.AskStatus(['t1', 't2'], 'U023BECGF', last_call=False)
        task.execute(self.bot, self.slack)
        task.execute(self.bot, self.slack)
        task.execute(self.bot, self.slack)

        self.assertEqual(len(self.bot.fast_queue), 1)
        task = self.bot.fast_queue.pop()
        self.assertIsInstance(task, pony.tasks.SendMessage)

    def test_execute(self):
        task = pony.tasks.AskStatus(['t1', 't2'], 'U023BECGF', last_call=False)
        task.execute(self.bot, self.slack)

        task = self.bot.fast_queue.pop()
        self.assertIsInstance(task, pony.tasks.SendMessage)
        self.assertEqual(task.to, 'U023BECGF')
        self.assertIn(task.text, Dictionary.PLEASE_REPORT)

    def test_execute_last_call(self):
        task = pony.tasks.AskStatus(['t1', 't2'], 'U023BECGF', last_call=True)
        task.execute(self.bot, self.slack)

        task = self.bot.fast_queue.pop()
        self.assertIsInstance(task, pony.tasks.SendMessage)
        self.assertEqual(task.to, 'U023BECGF')
        self.assertIn(task.text, Dictionary.PLEASE_REPORT_LAST_CALL)
