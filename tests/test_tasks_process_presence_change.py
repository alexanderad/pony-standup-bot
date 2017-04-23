from __future__ import absolute_import

import pony.tasks
from tests.test_base import BaseTest


class ProcessPresenceChangeTest(BaseTest):
    def setUp(self):
        super(ProcessPresenceChangeTest, self).setUp()
        self.bot.storage.set('users', [{'id': '_id1', 'deleted': False}])

    def test_execute_user_is_now_active(self):
        task = pony.tasks.ProcessPresenceChange('_id1', presence='active')
        task.execute(self.bot, self.slack)

        user = self.bot.get_user_by_id('_id1')
        self.assertEqual(user.get('presence'), 'active')

    def test_execute_is_online(self):
        self.assertFalse(self.bot.user_is_online('_id1'))

        task = pony.tasks.ProcessPresenceChange('_id1', presence='active')
        task.execute(self.bot, self.slack)

        self.assertTrue(self.bot.user_is_online('_id1'))

    def test_execute_is_away(self):
        task = pony.tasks.ProcessPresenceChange('_id1', presence='active')
        task.execute(self.bot, self.slack)
        self.assertTrue(self.bot.user_is_online('_id1'))

        task = pony.tasks.ProcessPresenceChange('_id1', presence='away')
        task.execute(self.bot, self.slack)
        self.assertFalse(self.bot.user_is_online('_id1'))
