from __future__ import absolute_import

from datetime import date, datetime

import freezegun
from flexmock import flexmock

import pony.tasks
from tests.test_base import BaseTest


class CheckReportsTest(BaseTest):
    def setUp(self):
        super(CheckReportsTest, self).setUp()
        self.task = pony.tasks.CheckReports()
        self.bot.config.update({
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
        })
        (flexmock(self.bot)
         .should_receive('get_user_by_name')
         .with_args('@sasha')
         .and_return({'id': '_sasha_id'}))

        # check reports might call the UserList update
        # but we are not interested in that in scope of this test
        (flexmock(self.bot.slack)
         .should_receive('api_call')
         .with_args('users.list', presence=1)
         .and_return({'members': []}))

    def test_is_weekend(self):
        saturday = date(2016, 12, 24)
        sunday = date(2016, 12, 25)

        self.assertTrue(self.task.is_weekend(saturday))
        self.assertTrue(self.task.is_weekend(sunday))

        monday = date(2016, 12, 26)
        self.assertFalse(self.task.is_weekend(monday))

    def test_is_holiday(self):
        self.bot.config.update({
            'holidays': {
                date(2016, 12, 25): 'Christmas'
            }
        })

        christmas = date(2016, 12, 25)
        self.assertTrue(self.task.is_holiday(self.bot, christmas))

        day_before_christmas = date(2016, 12, 24)
        self.assertFalse(self.task.is_holiday(self.bot, day_before_christmas))

    def test_is_reportable(self):
        self.bot.config.update({
            'holidays': {
                date(2016, 12, 25): 'Christmas'
            }
        })

        christmas = date(2016, 12, 25)
        self.assertFalse(self.task.is_reportable(self.bot, christmas))

        sunday = date(2016, 12, 25)
        self.assertFalse(self.task.is_reportable(self.bot, sunday))

        monday = date(2016, 12, 26)
        self.assertTrue(self.task.is_reportable(self.bot, monday))

    def test_init_report(self):
        report = self.task.init_empty_report(
            self.bot, self.bot.config['dev_team1'])

        self.assertDictEqual(
            report,
            {
                'reports': {
                    '_sasha_id': {
                        'report': [],
                        'department': None
                    }
                }
            }
        )

    def test_init_report_on_config_with_departments(self):
        self.bot.config['dev_team1']['users'] = [
            {'@sasha': 'Dev Department'}
        ]

        report = self.task.init_empty_report(
            self.bot, self.bot.config['dev_team1'])

        self.assertDictEqual(
            report,
            {
                'reports': {
                    '_sasha_id': {
                        'report': [],
                        'department': 'Dev Department'
                    }
                }
            }
        )

    def test_execute(self):
        with freezegun.freeze_time('2016-12-23 11:00'):
            self.task.execute(self.bot)

            task = self.bot.fast_queue.pop()
            self.assertIsInstance(task, pony.tasks.AskStatus)
            self.assertListEqual(task.teams, ['dev_team1'])
            self.assertEqual(task.user_id, '_sasha_id')

    def test_execute_too_early(self):
        with freezegun.freeze_time('2016-12-23 02:00'):
            self.task.execute(self.bot)

            with self.assertRaises(IndexError):
                self.bot.fast_queue.pop()

    def test_execute_too_late(self):
        with freezegun.freeze_time('2016-12-23 20:00'):
            self.task.execute(self.bot)

            task = self.bot.fast_queue.pop()
            self.assertIsInstance(task, pony.tasks.SendReportSummary)
            self.assertEqual(task.team, 'dev_team1')

    def test_execute_is_not_last_call_yet(self):
        # report by is set to 16.00
        with freezegun.freeze_time('2016-12-23 15:00'):
            self.task.execute(self.bot)

            task = self.bot.fast_queue.pop()
            self.assertIsInstance(task, pony.tasks.AskStatus)
            self.assertFalse(task.last_call)

            # no last call timestamp set yet
            self.assertIsNone(
                self.bot.storage.get('report')[
                    date(2016, 12, 23)
                ]['dev_team1'].get('last_call_at')
            )

    def test_execute_is_last_call(self):
        # report by is set to 16.00, last call is in 5 minutes
        with freezegun.freeze_time('2016-12-23 15:56'):
            self.task.execute(self.bot)

            task = self.bot.fast_queue.pop()
            self.assertIsInstance(task, pony.tasks.AskStatus)
            self.assertTrue(task.last_call)

            # last call timestamp is now set
            self.assertIsNotNone(
                self.bot.storage.get('report')[
                    date(2016, 12, 23)
                ]['dev_team1'].get('last_call_at')
            )

    def test_execute_report_summary_already_sent(self):
        with freezegun.freeze_time('2016-12-23 11:00'):
            self.task.execute(self.bot)

            task = self.bot.fast_queue.pop()
            self.assertIsInstance(task, pony.tasks.AskStatus)
            self.assertListEqual(task.teams, ['dev_team1'])
            self.assertEqual(task.user_id, '_sasha_id')

            # mark day as already reported
            self.bot.storage.set('report', {
                date(2016, 12, 23): {
                    'dev_team1': {
                        'reported_at': datetime.utcnow(),
                        'reports': {}
                    }
                }
            })

            self.task.execute(self.bot)
            with self.assertRaises(IndexError):
                self.bot.fast_queue.pop()

    def test_execute_day_is_weekend(self):
        with freezegun.freeze_time('2016-12-24 11:00'):
            self.task.execute(self.bot)
            with self.assertRaises(IndexError):
                self.bot.fast_queue.pop()

    def test_execute_day_is_holiday(self):
        with freezegun.freeze_time('2016-12-01 11:00'):
            self.task.execute(self.bot)

            task = self.bot.fast_queue.pop()
            self.assertIsInstance(task, pony.tasks.SendMessage)
            self.assertEqual(task.to, '#dev-team')
            self.assertIn('No Standup Today', task.text)
            self.assertIn('Romanian National Day', task.text)

            # this is sent only once (report is marked reported)
            self.task.execute(self.bot)
            with self.assertRaises(IndexError):
                self.bot.fast_queue.pop()

            self.assertIsNotNone(
                self.bot.storage.get('report')[
                    date(2016, 12, 1)
                ]['dev_team1'].get('reported_at')
            )
