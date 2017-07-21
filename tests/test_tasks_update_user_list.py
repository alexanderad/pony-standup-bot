from __future__ import absolute_import

from flexmock import flexmock

import pony.tasks
from tests.test_base import BaseTest


class UpdateUserListTest(BaseTest):
    def test_execute(self):
        task = pony.tasks.UpdateUserList()

        (flexmock(self.slack)
         .should_receive('api_call')
         .with_args('users.list', presence=1)
         .and_return(dict(
            members=[
                {'id': '_id1', 'deleted': False},
                {'id': '_id2', 'deleted': True},
            ]
        )))

        task.execute(self.bot, self.slack)
        self.assertEqual(
            self.bot.storage.get('users'),
            [{'id': '_id1', 'deleted': False}]
        )
