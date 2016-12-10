# coding=utf-8
import logging
import dateutil.tz
import dateutil.parser
from datetime import datetime, timedelta
from collections import defaultdict

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
            logging.info('Nothing to report for {}'.format(today))
            return

        team_config = bot.plugin_config[self.team]

        team_report = report.get(today, {}).get(self.team)
        if team_report is None:
            logging.info('Nothing to report for team {} at {}'.format(
                self.team, today))
            return

        if team_report.get('reported_at') is not None:
            logging.info('Already reported for team {} at {}'.format(
                self.team, today))
            return

        reports, offline_users, no_response_users = [], [], []
        for user_id, status in team_report.items():
            user_data = bot.get_user_by_id(user_id)
            if not user_data:
                logging.info('Unable to find user by id: {}'.format(user_id))
                continue

            full_name = user_data['profile'].get('real_name')
            color = '#{}'.format(user_data.get('color'))

            if not status.get('seen_online'):
                offline_users.append(full_name)
                continue

            if not status.get('reported_at'):
                no_response_users.append(full_name)
                continue

            reports.append({
                'color': color,
                'title': full_name,
                'text': u'\n'.join(status['report'])[:1024]
            })

        if no_response_users:
            reports.append({
                'color': '#ccc',
                'title': 'No Response Today',
                'text': u', '.join(no_response_users)
            })

        if offline_users:
            reports.append({
                'color': '#ccc',
                'title': 'Offline Today',
                'text': u', '.join(offline_users)
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
    def _is_reportable(self, bot, today):
        is_weekend = today.isoweekday() in (6, 7)
        is_holiday = today in bot.plugin_config.get('holidays', [])
        return not is_weekend and not is_holiday

    def _time_to_report(self, bot, report_by):
        tz = dateutil.tz.gettz(bot.plugin_config['timezone'])
        report_by = dateutil.parser.parse(report_by).replace(tzinfo=tz)
        now = datetime.now(dateutil.tz.tzlocal())
        return now >= report_by

    def _too_early_to_ask(self, bot, ask_earliest):
        tz = dateutil.tz.gettz(bot.plugin_config['timezone'])
        ask_earliest = dateutil.parser.parse(ask_earliest).replace(tzinfo=tz)
        now = datetime.now(dateutil.tz.tzlocal())
        return now < ask_earliest

    def _get_multi_team_users(self, bot, teams):
        user_teams = defaultdict(list)
        for team in teams:
            for user in bot.plugin_config[team]:
                user_teams[user].append(team)

        return {
            user: teams
            for user, teams in user_teams.items()
            if len(teams) > 1
        }

    def execute(self, bot, slack):
        # schedule next check
        bot.slow_queue.append(CheckReports())

        today = datetime.utcnow().date()

        is_reportable = self._is_reportable(bot, today)
        if not is_reportable:
            logging.info('Today is not reportable (weekend or holiday)')
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

            if self._too_early_to_ask(bot, team_config['ask_earliest']):
                logging.info('Too early to ask people on team {}'.format(team))
                continue

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

                bot.fast_queue.append(
                    AskStatus(team=team, user_id=user_id)
                )


class AskStatus(Task):
    def __init__(self, team, user_id):
        self.team = team
        self.user_id = user_id

    def execute(self, bot, slack):

        team_data = bot.plugin_config[self.team]

        current_lock = bot.get_user_lock(self.user_id)
        if current_lock:
            logging.info(
                'User {} is already locked for {}, will wait for them to '
                'respond'.format(self.user_id, current_lock))
            return

        if bot.is_online(self.user_id):
            today = datetime.utcnow().date()
            report = bot.storage.get('report')
            report[today][self.team][self.user_id]['seen_online'] = True
        else:
            logging.info(
                'User {} is not online, will try later'.format(self.user_id))
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
