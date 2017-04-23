from __future__ import absolute_import

import pony.tasks
from tests.test_base import BaseTest


class PonyTest(BaseTest):
    def setUp(self):
        super(PonyTest, self).setUp()
        self.bot.storage.set('users', [
            {'id': '_id1', 'name': 'user1', 'presence': 'active'}
        ])

    def test_get_user_by_id(self):
        self.assertDictEqual(
            self.bot.get_user_by_id('_id1'),
            {'id': '_id1', 'name': 'user1', 'presence': 'active'}
        )

    def test_get_user_by_id_no_such_user(self):
        self.assertIsNone(self.bot.get_user_by_id('_id2'))

    def test_get_user_by_name(self):
        self.assertDictEqual(
            self.bot.get_user_by_name('user1'),
            {'id': '_id1', 'name': 'user1', 'presence': 'active'}
        )

    def test_get_user_by_name_no_such_user(self):
        self.assertIsNone(self.bot.get_user_by_id('user2'))

    def test_user_is_online(self):
        self.assertTrue(self.bot.user_is_online('_id1'))

    def test_user_is_online_no_such_user(self):
        self.assertFalse(self.bot.user_is_online('_id2'))

    def test_user_is_online_user_away(self):
        self.bot.storage.set('users', [
            {'id': '_id1', 'name': 'user1', 'presence': 'away'}
        ])
        self.assertFalse(self.bot.user_is_online('_id1'))
