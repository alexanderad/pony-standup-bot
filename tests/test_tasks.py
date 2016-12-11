import freezegun
import unittest
from flexmock import flexmock

import pony.tasks
from pony.pony import StandupPonyPlugin


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.bot = StandupPonyPlugin(
            plugin_config={
                'db_file': ''
            }
        )
        self.slack = flexmock()


class SendMessageTest(BaseTest):
    def test_execute(self):
        task = pony.tasks.SendMessage('_to', '_text', [1, 2, 3])

        (flexmock(self.slack)
         .should_receive('api_call')
         .with_args(
            'chat.postMessage',
            channel='_to',
            text='_text',
            attachments=[1, 2, 3],
            as_user=True
        ))

        task.execute(self.bot, self.slack)


class UpdateUserListTest(BaseTest):
    def test_execute(self):
        task = pony.tasks.UpdateUserList()

        (flexmock(self.slack)
         .should_receive('api_call')
         .with_args('users.list')
         .and_return(dict(
            members=[
                {'user': '_id1', 'deleted': False},
                {'user': '_id2', 'deleted': True},
            ]
        )))

        task.execute(self.bot, self.slack)
        self.assertEqual(
            self.bot.storage.get('users'),
            [{'user': '_id1', 'deleted': False}]
        )


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


class SyncDBTest(BaseTest):
    def test_execute(self):
        task = pony.tasks.SyncDB()

        (flexmock(self.bot.storage)
         .should_receive('save')
         .once())

        task.execute(self.bot, self.slack)
        self.assertIsInstance(self.bot.slow_queue.pop(), pony.tasks.SyncDB)
