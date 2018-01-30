from __future__ import absolute_import

import time
from flexmock import flexmock

import pony.tasks
from tests.test_base import BaseTest


class SendMessageTest(BaseTest):
    def test_execute(self):
        task = pony.tasks.SendMessage('_to', '_text', [1, 2, 3])

        (flexmock(self.bot.slack.server)
         .should_receive('send_to_websocket')
         .with_args(dict(type='typing', channel='_to')))

        # send typing does imitate human typing by waiting up to 2 seconds
        (flexmock(time)
         .should_receive('sleep')
         .times(2))

        (flexmock(self.bot.slack)
         .should_receive('api_call')
         .with_args(
            'chat.postMessage',
            channel='_to',
            text='_text',
            attachments=[1, 2, 3],
            as_user=True
        ))

        task.execute(self.bot)
