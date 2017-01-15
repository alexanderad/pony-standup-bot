from __future__ import absolute_import

from datetime import datetime, date
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


class CheckReportsTest(BaseTest):
    def setUp(self):
        super(CheckReportsTest, self).setUp()
        self.task = pony.tasks.CheckReports()
        self.bot.plugin_config = {
            'timezone': 'UTC',
            'holidays': {
                date(2016, 12, 1): 'Romanian National Day'
            },
            'active_teams': ['dev_team1'],
            'dev_team1': {
                'name': 'Dev Team 1',
                'post_summary_to': '#dev-team',
                'report_by': '16:00',
                'ask_earliest': '09:00',
                'users': [
                    '@sasha'
                ]
            }
        }
        (flexmock(self.bot)
         .should_receive('get_user_by_name')
         .with_args('@sasha')
         .and_return({'id': '_sasha_id'}))

    def test_is_weekend(self):
        saturday = date(2016, 12, 24)
        sunday = date(2016, 12, 25)

        self.assertTrue(self.task.is_weekend(saturday))
        self.assertTrue(self.task.is_weekend(sunday))

        monday = date(2016, 12, 26)
        self.assertFalse(self.task.is_weekend(monday))

    def test_is_holiday(self):
        self.bot.plugin_config = {
            'holidays': {
                date(2016, 12, 25): 'Christmas'
            }
        }

        christmas = date(2016, 12, 25)
        self.assertTrue(self.task.is_holiday(self.bot, christmas))

        day_before_christmas = date(2016, 12, 24)
        self.assertFalse(self.task.is_holiday(self.bot, day_before_christmas))

    def test_is_reportable(self):
        self.bot.plugin_config = {
            'holidays': {
                date(2016, 12, 25): 'Christmas'
            }
        }

        christmas = date(2016, 12, 25)
        self.assertFalse(self.task.is_reportable(self.bot, christmas))

        sunday = date(2016, 12, 25)
        self.assertFalse(self.task.is_reportable(self.bot, sunday))

        monday = date(2016, 12, 26)
        self.assertTrue(self.task.is_reportable(self.bot, monday))

    def test_init_report(self):
        report = self.task.init_empty_report(
            self.bot, self.bot.plugin_config['dev_team1'])

        self.assertDictEqual(
            report,
            {
                '_sasha_id': {
                    'report': []
                }
            }
        )

    def test_execute(self):
        with freezegun.freeze_time('2016-12-23 11:00'):
            self.task.execute(self.bot, self.slack)

            task = self.bot.fast_queue.pop()
            self.assertIsInstance(task, pony.tasks.AskStatus)
            self.assertListEqual(task.teams, ['dev_team1'])
            self.assertEqual(task.user_id, '_sasha_id')

    def test_execute_too_early(self):
        with freezegun.freeze_time('2016-12-23 02:00'):
            self.task.execute(self.bot, self.slack)

            with self.assertRaises(IndexError):
                self.bot.fast_queue.pop()

    def test_execute_too_late(self):
        with freezegun.freeze_time('2016-12-23 20:00'):
            self.task.execute(self.bot, self.slack)

            task = self.bot.fast_queue.pop()
            self.assertIsInstance(task, pony.tasks.SendReportSummary)
            self.assertEqual(task.team, 'dev_team1')

    def test_execute_report_summary_already_sent(self):
        with freezegun.freeze_time('2016-12-23 11:00'):
            self.task.execute(self.bot, self.slack)

            task = self.bot.fast_queue.pop()
            self.assertIsInstance(task, pony.tasks.AskStatus)
            self.assertListEqual(task.teams, ['dev_team1'])
            self.assertEqual(task.user_id, '_sasha_id')

            # mark day as already reported
            self.bot.storage.set('report', {
                date(2016, 12, 23): {
                    'dev_team1': {
                        'reported_at': datetime.utcnow()
                    }
                }
            })

            self.task.execute(self.bot, self.slack)
            with self.assertRaises(IndexError):
                self.bot.fast_queue.pop()

    def test_execute_day_is_weekend(self):
        with freezegun.freeze_time('2016-12-24 11:00'):
            self.task.execute(self.bot, self.slack)
            with self.assertRaises(IndexError):
                self.bot.fast_queue.pop()

    def test_execute_day_is_holiday(self):
        with freezegun.freeze_time('2016-12-01 11:00'):
            self.task.execute(self.bot, self.slack)

            task = self.bot.fast_queue.pop()
            self.assertIsInstance(task, pony.tasks.SendMessage)
            self.assertEqual(task.to, '#dev-team')
            self.assertEqual(task.text, 'No Standup Today')

            # this is sent only once (report is marked reported)
            self.task.execute(self.bot, self.slack)
            with self.assertRaises(IndexError):
                self.bot.fast_queue.pop()

            self.assertIsNotNone(
                self.bot.storage.get('report')[
                    date(2016, 12, 1)
                ]['dev_team1'].get('reported_at')
            )


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
        self.assertIsNone(task.execute(self.bot, self.slack))

    def test_execute_skips_bot_messages(self):
        task = pony.tasks.ReadMessage({'bot_id': '_bot_id'})
        self.assertIsNone(task.execute(self.bot, self.slack))

    def test_execute_reads_status_message(self):
        self.bot.storage.set('ims', [{'id': '_im_channel_id'}])
        data = {
            'type': 'message',
            'user': '_user_id',
            'channel': '_im_channel_id',
            'text': '_text'
        }

        task = pony.tasks.ReadMessage(data)

        self.assertIsNone(task.execute(self.bot, self.slack))

        read_message_task = self.bot.fast_queue.pop()
        self.assertIsInstance(read_message_task, pony.tasks.ReadStatusMessage)
        self.assertDictEqual(read_message_task.data, data)


class ReadMessageEditTest(BaseTest):
    def setUp(self):
        super(ReadMessageEditTest, self).setUp()
        self.bot.plugin_config = {
            'active_teams': ['dev_team1', 'dev_team2'],
        }
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
        task.execute(self.bot, self.slack)

    def test_execute_single_team_user(self):
        today = datetime.utcnow().date()
        self.bot.storage.set('report', {
            today: {
                'dev_team1': {
                    'U04RVVBAY': {
                        'report': [
                            'Found and fixed Pony bug',
                            'Left to party afterwards'
                        ]
                    }
                }
            }
        })

        task = pony.tasks.ReadMessageEdit(self.data)
        task.execute(self.bot, self.slack)

        report = self.bot.storage.get('report')[today]['dev_team1']
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
                    'U04RVVBAY': {
                        'report': [
                            'Found and fixed Pony bug',
                            'Left to party afterwards'
                        ]
                    }
                },
                'dev_team2': {
                    'U04RVVBAY': {
                        'report': [
                            'Found and fixed Pony bug',
                            'Left to party afterwards'
                        ]
                    }
                }
            }
        })

        task = pony.tasks.ReadMessageEdit(self.data)
        task.execute(self.bot, self.slack)

        report1 = self.bot.storage.get('report')[today]['dev_team1']
        self.assertIsNotNone(report1['U04RVVBAY']['edited_at'])
        self.assertListEqual(
            report1['U04RVVBAY']['report'],
            [
                'Found and fixed Pony bug',
                'Worked hard the rest of the day'
            ]
        )

        report2 = self.bot.storage.get('report')[today]['dev_team2']
        self.assertIsNotNone(report2['U04RVVBAY']['edited_at'])
        self.assertListEqual(
            report2['U04RVVBAY']['report'],
            [
                'Found and fixed Pony bug',
                'Worked hard the rest of the day'
            ]
        )
