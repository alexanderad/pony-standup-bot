from __future__ import absolute_import

from datetime import datetime

import pony.tasks
from tests.test_base import BaseTest


class ReadMessageTest(BaseTest):
    def setUp(self):
        super(ReadMessageTest, self).setUp()
        self.bot.storage.set('ims', [])

    def test_is_not_a_bot_message(self):
        task = pony.tasks.ReadMessage({})
        self.assertFalse(task.is_bot_message())

    def test_is_bot_message(self):
        task = pony.tasks.ReadMessage({'bot_id': '_bot_id'})
        self.assertTrue(task.is_bot_message())

    def test_is_not_a_direct_message(self):
        task = pony.tasks.ReadMessage({
            'type': 'message',
            'user': '_user_id',
            'channel': '_not_im_channel'
        })
        self.assertFalse(task.is_direct_message(self.bot))

    def test_is_direct_message(self):
        self.bot.storage.set('ims', [{'id': '_im_channel_id'}])

        task = pony.tasks.ReadMessage({
            'type': 'message',
            'user': '_user_id',
            'channel': '_im_channel_id'
        })
        self.assertTrue(task.is_direct_message(self.bot))

    def test_execute_empty_payload(self):
        task = pony.tasks.ReadMessage({})
        self.assertIsNone(task.execute(self.bot))

    def test_execute_skips_bot_messages(self):
        task = pony.tasks.ReadMessage({'bot_id': '_bot_id'})
        self.assertIsNone(task.execute(self.bot))

    def test_execute_reads_status_message(self):
        self.bot.storage.set('ims', [{'id': '_im_channel_id'}])
        data = {
            'type': 'message',
            'user': '_user_id',
            'channel': '_im_channel_id',
            'text': '_text'
        }

        task = pony.tasks.ReadMessage(data)

        self.assertIsNone(task.execute(self.bot))

        read_message_task = self.bot.fast_queue.pop()
        self.assertIsInstance(read_message_task, pony.tasks.ReadStatusMessage)
        self.assertDictEqual(read_message_task.data, data)


class ReadMessageEditTest(BaseTest):
    def setUp(self):
        super(ReadMessageEditTest, self).setUp()
        self.bot.config.update({
            'active_teams': ['dev_team1', 'dev_team2'],
        })
        self.bot.storage.set('report', {})
        self.data = {
            'event_ts': '1484475451.173471',
            'ts': '1484475451.000005',
            'type': 'message',
            'hidden': True,
            'channel': 'D3AV4E6BZ',
            'subtype': 'message_changed',
            'message': {
                'text': 'Worked hard the rest of the day', 'type': 'message',
                'user': 'U04RVVBAY', 'ts': '1484475444.000003',
                'edited': {
                    'user': 'U04RVVBAY',
                    'ts': '1484475451.000000'
                }
            },
            'previous_message': {
                'text': 'Left to party afterwards',
                'type': 'message',
                'user': 'U04RVVBAY',
                'ts': '1484475444.000003'
            }
        }

    def test_execute_empty_report_or_no_user(self):
        task = pony.tasks.ReadMessageEdit(self.data)
        task.execute(self.bot)

    def test_execute_single_team_user(self):
        today = datetime.utcnow().date()
        self.bot.storage.set('report', {
            today: {
                'dev_team1': {
                    'reports': {
                        'U04RVVBAY': {
                            'report': [
                                'Found and fixed Pony bug',
                                'Left to party afterwards'
                            ]
                        }
                    }
                }
            }
        })

        task = pony.tasks.ReadMessageEdit(self.data)
        task.execute(self.bot)

        report = self.bot.storage.get('report')[today]['dev_team1']['reports']
        self.assertIsNotNone(report['U04RVVBAY']['edited_at'])
        self.assertListEqual(
            report['U04RVVBAY']['report'],
            [
                'Found and fixed Pony bug',
                'Worked hard the rest of the day'
            ]
        )

    def test_execute_multi_team_user(self):
        today = datetime.utcnow().date()
        self.bot.storage.set('report', {
            today: {
                'dev_team1': {
                    'reports': {
                        'U04RVVBAY': {
                            'report': [
                                'Found and fixed Pony bug',
                                'Left to party afterwards'
                            ]
                        }
                    }
                },
                'dev_team2': {
                    'reports': {
                        'U04RVVBAY': {
                            'report': [
                                'Found and fixed Pony bug',
                                'Left to party afterwards'
                            ]
                        }
                    }
                }
            }
        })

        task = pony.tasks.ReadMessageEdit(self.data)
        task.execute(self.bot)

        report1 = self.bot.storage.get('report')[today]['dev_team1']['reports']
        self.assertIsNotNone(report1['U04RVVBAY']['edited_at'])
        self.assertListEqual(
            report1['U04RVVBAY']['report'],
            [
                'Found and fixed Pony bug',
                'Worked hard the rest of the day'
            ]
        )

        report2 = self.bot.storage.get('report')[today]['dev_team2']['reports']
        self.assertIsNotNone(report2['U04RVVBAY']['edited_at'])
        self.assertListEqual(
            report2['U04RVVBAY']['report'],
            [
                'Found and fixed Pony bug',
                'Worked hard the rest of the day'
            ]
        )
