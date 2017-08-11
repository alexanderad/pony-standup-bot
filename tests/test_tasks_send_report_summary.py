from __future__ import absolute_import

from datetime import datetime

from flexmock import flexmock

import pony.tasks
from tests.test_base import BaseTest


class SendReportSummaryTest(BaseTest):
    def setUp(self):
        super(SendReportSummaryTest, self).setUp()
        self.bot.storage.set('report', {})
        self.bot.plugin_config = {
            '_dummy_team': {
                'post_summary_to': '#dummy-channel',
                'name': 'Dummy Team'
            }
        }

        (flexmock(self.bot)
         .should_receive('get_user_by_id')
         .with_args('_user_id')
         .and_return({
            'id': '_user_id',
            'color': 'aabbcc',
            'profile': {
                'real_name': 'Dummy User'
            }
        }))

        (flexmock(self.bot)
            .should_receive('get_user_by_name')
            .with_args('@user')
            .and_return({
            'id': '_user_id',
            'color': 'aabbcc',
            'profile': {
                'real_name': 'Dummy User'
            }
        }))

    def test_get_user_avatar_is_failsafe(self):
        (flexmock(self.slack)
         .should_receive('api_call')
         .with_args('users.list')
         .and_return(dict(members=[])))

        task = pony.tasks.SendReportSummary('_dummy_team')
        self.assertIsNone(task.get_user_avatar(self.slack, '_user_id'))

    def test_get_user_avatar(self):
        (flexmock(self.slack)
         .should_receive('api_call')
         .with_args('users.list')
         .and_return({
            'members': [{
                'id': '_user_id',
                'profile': {
                    'image_192': '_image_192_url',
                }
            }]
        }))

        task = pony.tasks.SendReportSummary('_dummy_team')
        self.assertEqual(
            task.get_user_avatar(self.slack, '_user_id'), '_image_192_url')

    def test_get_user_avatar_lazy_loads_profiles(self):
        (flexmock(self.slack)
         .should_receive('api_call')
         .with_args('users.list')
         .and_return(dict(members=[]))
         .times(1))

        task = pony.tasks.SendReportSummary('_dummy_team')
        self.assertIsNone(task.get_user_avatar(self.slack, '_user_id'))
        self.assertIsNone(task.get_user_avatar(self.slack, '_user_id'))
        self.assertIsNone(task.get_user_avatar(self.slack, '_user_id'))

    def test_execute_no_reports(self):
        self.bot.storage.set('report', {})

        task = pony.tasks.SendReportSummary('_dummy_team')
        self.assertIsNone(task.execute(self.bot, self.slack))

    def test_execute_no_report_for_this_team(self):
        self.bot.storage.set('report', {
            datetime.utcnow().date(): {}
        })

        task = pony.tasks.SendReportSummary('_dummy_team')
        self.assertIsNone(task.execute(self.bot, self.slack))

    def test_execute_report_already_sent(self):
        self.bot.storage.set('report', {
            datetime.utcnow().date(): {
                '_dummy_team': {
                    'reported_at': datetime.utcnow()
                }
            }
        })

        task = pony.tasks.SendReportSummary('_dummy_team')
        self.assertIsNone(task.execute(self.bot, self.slack))
        self.assertEqual(len(self.bot.fast_queue), 0)

    def test_execute_user_not_seen_online(self):
        self.bot.plugin_config['_dummy_team']['users'] = ['@user']
        self.bot.storage.set('report', {
            datetime.utcnow().date(): {
                '_dummy_team': {
                    'reports': {
                        '_user_id': {
                            'seen_online': False
                        }
                    }
                }
            }
        })

        task = pony.tasks.SendReportSummary('_dummy_team')
        self.assertIsNone(task.execute(self.bot, self.slack))

        report = self.bot.fast_queue.pop()
        self.assertIsInstance(report, pony.tasks.SendMessage)
        self.assertEqual(report.to, '#dummy-channel')
        self.assertIn('Summary for Dummy Team', report.text)
        self.assertIn(
            {'color': '#ccc', 'title': 'Offline', 'text': 'Dummy User'},
            report.attachments
        )

    def test_execute_user_returned_no_response(self):
        self.bot.plugin_config['_dummy_team']['users'] = ['@user']
        self.bot.storage.set('report', {
            datetime.utcnow().date(): {
                '_dummy_team': {
                    'reports': {
                        '_user_id': {
                            'seen_online': True
                        }
                    }
                }
            }
        })

        task = pony.tasks.SendReportSummary('_dummy_team')
        self.assertIsNone(task.execute(self.bot, self.slack))

        report = self.bot.fast_queue.pop()
        self.assertIsInstance(report, pony.tasks.SendMessage)
        self.assertEqual(report.to, '#dummy-channel')
        self.assertIn('Summary for Dummy Team', report.text)
        self.assertIn(
            {'color': '#ccc', 'title': 'No Response', 'text': 'Dummy User'},
            report.attachments
        )

    def test_execute(self):
        self.bot.plugin_config['_dummy_team']['users'] = ['@user']
        self.bot.storage.set('report', {
            datetime.utcnow().date(): {
                '_dummy_team': {
                    'reports': {
                        '_user_id': {
                            'seen_online': True,
                            'reported_at': datetime.utcnow(),
                            'report': [
                                'line1',
                                'line2'
                            ]
                        }
                    }
                }
            }
        })

        task = pony.tasks.SendReportSummary('_dummy_team')

        (flexmock(task)
         .should_receive('get_user_avatar')
         .with_args(self.slack, '_user_id')
         .and_return('_dummy_user_avatar_url'))

        self.assertIsNone(task.execute(self.bot, self.slack))

        report = self.bot.fast_queue.pop()
        self.assertIsInstance(report, pony.tasks.SendMessage)
        self.assertEqual(report.to, '#dummy-channel')
        self.assertIn('Summary for Dummy Team', report.text)
        report_line = report.attachments.pop()
        self.assertEqual(report_line['title'], 'Dummy User')
        self.assertEqual(report_line['text'], 'line1\nline2')
        self.assertEqual(report_line['color'], '#aabbcc')
        self.assertEqual(report_line['thumb_url'], '_dummy_user_avatar_url')
        self.assertIsNotNone(report_line['ts'])

    def test_execute_when_user_has_department_assigned(self):
        self.bot.plugin_config['_dummy_team']['users'] = ['@user']
        self.bot.storage.set('report', {
            datetime.utcnow().date(): {
                '_dummy_team': {
                    'reports': {
                        '_user_id': {
                            'seen_online': True,
                            'department': 'Dev Department',
                            'reported_at': datetime.utcnow(),
                            'report': [
                                'line1',
                                'line2'
                            ]
                        }
                    }
                }
            }
        })

        task = pony.tasks.SendReportSummary('_dummy_team')

        (flexmock(task)
         .should_receive('get_user_avatar')
         .with_args(self.slack, '_user_id')
         .and_return('_dummy_user_avatar_url'))

        self.assertIsNone(task.execute(self.bot, self.slack))

        report = self.bot.fast_queue.pop()

        report_line = report.attachments.pop()
        self.assertEqual(report_line['footer'], 'Dev Department')
