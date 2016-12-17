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
        logging.info(u'Sending message "{}" to {}'.format(self.text, self.to))
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
        logging.info('Building report summary for {}'.format(self.team))

        if today not in report:
            logging.debug('Nothing to report for today')
            return

        team_config = bot.plugin_config[self.team]

        team_report = report[today].get(self.team)
        if team_report is None:
            logging.debug('Nothing to report for this team')
            return

        if team_report.get('reported_at') is not None:
            logging.debug('Already reported today')
            return

        reports, offline_users, no_response_users = [], [], []
        for user_id, data in team_report.items():
            user_data = bot.get_user_by_id(user_id)
            if not user_data:
                logging.error('Unable to find user by id: {}'.format(user_id))
                continue

            full_name = user_data['profile'].get('real_name')
            color = '#{}'.format(user_data.get('color'))

            if not data.get('seen_online'):
                offline_users.append(full_name)
                continue

            if not data.get('reported_at'):
                no_response_users.append(full_name)
                continue

            reports.append({
                'color': color,
                'title': full_name,
                'text': u'\n'.join(data['report'])[:1024]
            })

        if no_response_users:
            reports.append({
                'color': '#ccc',
                'title': 'No Response',
                'text': u', '.join(no_response_users)
            })

        if offline_users:
            reports.append({
                'color': '#ccc',
                'title': 'Offline',
                'text': u', '.join(offline_users)
            })

        if reports:
            channel = team_config['post_summary_to']
            bot.fast_queue.append(
                SendMessage(
                    to=channel,
                    text='Summary for {}: {}'.format(
                        team_config['name'], today.strftime('%A, %d %B')
                    ),
                    attachments=reports
                )
            )

            team_report['reported_at'] = datetime.utcnow()

            logging.info('Reported status for {}'.format(self.team))


class CheckReports(Task):
    def _is_reportable(self, bot, today):
        is_weekend = today.isoweekday() in (6, 7)
        is_holiday = today in bot.plugin_config.get('holidays', [])
        return not is_weekend and not is_holiday

    def _is_time_to_send_summary(self, bot, report_by):
        tz = dateutil.tz.gettz(bot.plugin_config['timezone'])
        report_by = dateutil.parser.parse(report_by).replace(tzinfo=tz)
        now = datetime.now(dateutil.tz.tzlocal())
        return now >= report_by

    def _is_too_early_to_ask(self, bot, ask_earliest):
        tz = dateutil.tz.gettz(bot.plugin_config['timezone'])
        ask_earliest = dateutil.parser.parse(ask_earliest).replace(tzinfo=tz)
        now = datetime.now(dateutil.tz.tzlocal())
        return now < ask_earliest

    def _init_empty_report(self, bot, team_config):
        team_report = dict()
        for user in team_config['users']:
            user_data = bot.get_user_by_name(user)
            if not user_data:
                logging.error('Unable to find user by name {}'.format(user))
                continue

            team_report[user_data['id']] = {'report': []}

        return team_report

    def execute(self, bot, slack):
        # schedule next check
        bot.slow_queue.append(CheckReports())

        today = datetime.utcnow().date()

        is_reportable = self._is_reportable(bot, today)
        if not is_reportable:
            logging.debug('Today is not reportable (weekend or holiday)')
            return

        report = bot.storage.get('report', {})
        if today not in report:
            logging.info('Initializing empty report for {}'.format(today))
            report[today] = dict()

        # ensure report entries exist for current day and all the teams
        teams = bot.plugin_config['active_teams']
        for team in teams:
            team_config = bot.plugin_config[team]

            if team not in report[today]:
                logging.info(
                    'Initializing empty report for {} {}'.format(
                        team, today))
                report[today][team] = self._init_empty_report(bot, team_config)

        teams_by_user = defaultdict(list)
        for team, users_data in report[today].items():
            for user_id in users_data.keys():
                teams_by_user[user_id].append(team)

        for team in teams:
            team_config = bot.plugin_config[team]
            team_report = report[today][team]

            if team_report.get('reported_at'):
                logging.debug('Team {} already reported'.format(team))
                continue

            if self._is_time_to_send_summary(bot, team_config['report_by']):
                logging.debug('It is time to send summary for {}'.format(team))
                bot.fast_queue.append(SendReportSummary(team))
                continue

            if self._is_too_early_to_ask(bot, team_config['ask_earliest']):
                logging.debug('Too early to ask people on {}'.format(team))
                continue

            for user_id in team_report.keys():

                if team_report[user_id].get('reported_at'):
                    continue

                bot.fast_queue.append(
                    AskStatus(teams=teams_by_user[user_id], user_id=user_id)
                )


class AskStatus(Task):
    def __init__(self, teams, user_id):
        self.teams = teams
        self.user_id = user_id

    def execute(self, bot, slack):
        current_lock = bot.get_user_lock(self.user_id)
        if current_lock:
            logging.debug(
                'User {} is already locked for {}, will wait for them to '
                'respond'.format(self.user_id, current_lock))
            return

        if bot.user_is_online(self.user_id):
            today = datetime.utcnow().date()
            report = bot.storage.get('report')
            for team in self.teams:
                report[today][team][self.user_id]['seen_online'] = True
        else:
            logging.debug(
                'User {} is not online, will try later'.format(self.user_id))
            return

        # lock this user conversation, worst case till the end of day
        now = datetime.utcnow()
        expire_in = (
            timedelta(hours=24) - timedelta(hours=now.hour, minutes=now.minute)
        ).total_seconds()
        bot.lock_user(self.user_id, self.teams, expire_in)

        logging.info('Asked user {} their status for {}'.format(
            self.user_id, self.teams))

        bot.fast_queue.append(
            SendMessage(
                to=self.user_id,
                text=Dictionary.pick(
                    phrases=Dictionary.PLEASE_REPORT,
                    user_id=self.user_id
                )
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
        teams = bot.get_user_lock(user_id)
        if teams is None:
            logging.debug(
                'User {} is not known to have any active context'.format(
                    user_id))
            return

        # update status
        today = datetime.utcnow().date()
        report, is_first_line = bot.storage.get('report'), False
        for team in teams:
            user_report = report[today][team][user_id]
            user_report['reported_at'] = datetime.utcnow()
            is_first_line = len(user_report['report']) == 0
            user_report['report'].append(self.data['text'])

        logging.info(u'User {} says "{}"'.format(user_id, self.data['text']))

        # give user extra seconds to add more lines in context of this lock
        bot.lock_user(user_id, teams, expire_in=90)
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
