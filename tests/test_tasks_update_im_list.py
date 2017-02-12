from __future__ import absolute_import

from flexmock import flexmock

import pony.tasks
from tests.test_base import BaseTest


class UpdateIMListTest(BaseTest):
    def test_execute(self):
        task = pony.tasks.UpdateIMList()

        (flexmock(self.slack)
         .should_receive('api_call')
         .with_args('im.list')
         .and_return(dict(
            ims=[
                {'id': '_id1', 'is_im': True, 'is_user_deleted': False},
                {'id': '_id2', 'is_im': False, 'is_user_deleted': False},
                {'id': '_id3', 'is_im': True, 'is_user_deleted': True},
            ]
        )))

        task.execute(self.bot, self.slack)
        self.assertEqual(
            self.bot.storage.get('ims'),
            [{'id': '_id1', 'is_im': True, 'is_user_deleted': False}]
        )
