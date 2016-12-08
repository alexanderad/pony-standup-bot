# coding=utf-8
import logging
import dateutil.tz
import dateutil.parser
from datetime import datetime, timedelta

from .dictionary import Dictionary


class Task(object):
    def execute(self, bot, slack):
        pass


class SendMessage(Task):
    def __init__(self, to, text, attachments=None):
        self.to = to
        self.text = text
        self.attachments = attachments

    def execute(self, bot, slack):
        slack.api_call(
            'chat.postMessage',
            channel=self.to,
            text=self.text,
            attachments=self.attachments,
            as_user=True
        )


class UpdateUserList(Task):
    def execute(self, bot, slack):
        logging.info('Updating user list')
        users = [
            user for user in slack.api_call('users.list')['members']
            if not user['deleted']
        ]

        bot.storage.set('users', users)


class UpdateIMList(Task):
    def execute(self, bot, slack):
        logging.info('Updating IM list')
        ims = [
            im for im in slack.api_call('im.list')['ims']
            if im['is_im'] and not im['is_user_deleted']
        ]

        bot.storage.set('ims', ims)


class SendReportSummary(Task):
    def __init__(self, team):
        self.team = team

    def execute(self, bot, slack):
        report = bot.storage.get('report')

        today = datetime.utcnow().date()
        if today not in report:
            logging.error('Nothing to report for {}'.format(today))
            return

        team_config = bot.plugin_config[self.team]

        team_report = report.get(today, {}).get(self.team)
        if team_report is None:
            logging.error('Nothing to report for team {} at {}'.format(
                self.team, today))
            return

        if team_report.get('reported_at') is not None:
            logging.error('Already reported for team {} at {}'.format(
                self.team, today))
            return

        reports = []
        offline_today = []
        for user_id, status in team_report.items():
            user_data = bot.get_user_by_id(user_id)
            if not user_data:
                continue

            full_name = user_data['profile'].get('real_name')
            color = '#{}'.format(user_data.get('color'))

            if not status['seen_online']:
                offline_today.append(full_name)
                continue

            if not status.get('reported_at'):
                reports.append({
                    'color': color,
                    'title': full_name,
                    'text': 'said nothing'
                })
                continue

            reports.append({
                'color': color,
                'title': full_name,
                'text': u'\n'.join(status['report'])[:1024]
            })

        if offline_today:
            reports.append({
                'color': '#f2f2f2',
                'title': 'Offline today',
                'text': u', '.join(offline_today)
            })

        if reports:
            channel = team_config['post_summary_to']
            bot.fast_queue.append(
                SendMessage(
                    to=channel,
                    text='Standup Summary for Today',
                    attachments=reports
                )
            )

            team_report['reported_at'] = datetime.utcnow()

            logging.info('Reported status for team {}'.format(self.team))

        bot.fast_queue.append(UnlockUsers(team=self.team))


class UnlockUsers(Task):
    def __init__(self, team):
        self.team = team

    def execute(self, bot, slack):
        team_config = bot.plugin_config[self.team]

        for user in team_config['users']:
            user_data = bot.get_user_by_name(user)
            if not user_data:
                continue

            user_id = user_data['id']
            user_lock = bot.get_user_lock(user_id)
            if user_lock and user_lock == self.team:
                bot.unlock_user(user_id)


class CheckReports(Task):
    def _is_reportable(self, today):
        is_weekend = today.isoweekday() in (6, 7)
        return not is_weekend

    def _time_to_report(self, bot, report_by):
        bot_tz = dateutil.tz.gettz(bot.plugin_config['timezone'])
        report_by = dateutil.parser.parse(report_by).replace(tzinfo=bot_tz)
        now = datetime.now(dateutil.tz.tzlocal())
        return now >= report_by

    def execute(self, bot, slack):
        # schedule next check
        bot.slow_queue.append(CheckReports())

        today = datetime.utcnow().date()

        is_reportable = self._is_reportable(today)
        if not is_reportable:
            return

        report = bot.storage.get('report', {})
        if today not in report:
            report[today] = dict()

        teams = bot.plugin_config['active_teams']
        for team in teams:
            if team not in report[today]:
                report[today][team] = {}

            team_report = report[today][team]
            team_config = bot.plugin_config[team]

            if team_report.get('reported_at'):
                return

            if self._time_to_report(bot, team_config['report_by']):
                bot.fast_queue.append(SendReportSummary(team))
                return

            for user in team_config['users']:
                user_data = bot.get_user_by_name(user)
                if not user_data:
                    continue

                user_id = user_data['id']

                if user_id not in team_report:
                    team_report[user_id] = {'report': []}

                if team_report[user_id].get('reported_at'):
                    continue

                team_report[user_id]['seen_online'] = bot.is_online(user_id)

                bot.fast_queue.append(
                    AskStatus(team=team, user_id=user_id)
                )


class AskStatus(Task):
    def __init__(self, team, user_id):
        self.team = team
        self.user_id = user_id

    def execute(self, bot, slack):
        team_data = bot.plugin_config[self.team]

        if not bot.is_online(self.user_id):
            logging.info(
                'User {} is not online, will try later'.format(self.user_id))
            return

        current_lock = bot.get_user_lock(self.user_id)
        if current_lock:
            logging.info(
                'User {} is already locked for {}, will wait for them to '
                'respond'.format(self.user_id, current_lock))
            return

        # lock this user conversation, worst case till the end of day
        now = datetime.utcnow()
        expire_in = (
            timedelta(hours=24) - timedelta(hours=now.hour, minutes=now.minute)
        ).total_seconds()
        bot.lock_user(self.user_id, self.team, expire_in)

        logging.info('Asked user {} their status for team {}'.format(
            self.user_id, self.team))
        bot.fast_queue.append(
            SendMessage(
                to=self.user_id,
                text=Dictionary.pick(
                    phrases=Dictionary.PLEASE_REPORT,
                    user_id=self.user_id
                ).format(team_data['name'])
            )
        )


class ReadMessage(Task):
    def __init__(self, data):
        self.data = data

    def is_dm(self, bot):
        return all([
            self.data.get('type') == 'message',
            'user' in self.data,
            'subtype' not in self.data,
            any([
                im['id'] == self.data['channel']
                for im in bot.storage.get('ims')
            ])
        ])

    def execute(self, bot, slack):
        if not self.is_dm(bot):
            return

        user_id = self.data['user']

        # check if there are any active context for this user
        team = bot.get_user_lock(user_id)
        if team is None:
            return

        # update status for most recent locked team
        today = datetime.utcnow().date()
        report = bot.storage.get('report')
        user_report = report[today][team][user_id]
        user_report['reported_at'] = datetime.utcnow()
        is_first_line = len(user_report['report']) == 0
        user_report['report'].append(self.data['text'])

        logging.info(u'User {} says "{}"'.format(user_id, self.data['text']))

        # give user extra seconds to add more lines in context of this lock
        bot.lock_user(user_id, team, expire_in=90)
        if is_first_line:
            bot.fast_queue.append(
                SendMessage(
                    to=user_id,
                    text=Dictionary.pick(
                        phrases=Dictionary.THANKS,
                        user_id=user_id
                    )
                )
            )
        else:
            bot.fast_queue.append(
                SendMessage(to=user_id, text="Ok, I'll add that too.")
            )


class SyncDB(Task):
    def execute(self, bot, slack):
        bot.storage.save()
        bot.slow_queue.append(SyncDB())