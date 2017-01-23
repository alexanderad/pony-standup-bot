# coding=utf-8
import logging
import calendar
import dateutil.tz
import dateutil.parser
import random

from datetime import datetime, timedelta
from collections import defaultdict

from .dictionary import Dictionary


class Task(object):
    """Single task."""
    def execute(self, bot, slack):
        pass


class SendMessage(Task):
    """Sends a single message to channel or user."""
    def __init__(self, to, text, attachments=None):
        self.to = to
        self.text = text
        self.attachments = attachments

    def get_im_channel(self, bot, to):
        for im in bot.storage.get('ims', []):
            if im.get('user', None) == self.to:
                return im['id']

        return to

    def execute(self, bot, slack):
        im_channel = self.get_im_channel(bot, self.to)

        logging.info(u'Sending message "{}" to {} (typing event to {})'.format(
            self.text, self.to, im_channel))

        bot.send_typing(to=im_channel)
        slack.api_call(
            'chat.postMessage',
            channel=self.to,
            text=self.text,
            attachments=self.attachments,
            as_user=True
        )


class UpdateUserList(Task):
    """Updates team user list."""
    def execute(self, bot, slack):
        logging.info('Updating user list')
        users = [
            user for user in slack.api_call('users.list')['members']
            if not user['deleted']
        ]

        bot.storage.set('users', users)


class UpdateIMList(Task):
    """Updates current IM list."""
    def execute(self, bot, slack):
        logging.info('Updating IM list')
        ims = [
            im for im in slack.api_call('im.list')['ims']
            if im['is_im'] and not im['is_user_deleted']
        ]

        bot.storage.set('ims', ims)


class SyncDB(Task):
    """Syncs in-memory database to file."""
    def execute(self, bot, slack):
        bot.storage.save()
        bot.slow_queue.append(SyncDB())


class SendReportSummary(Task):
    """Sends a report summary to team channel."""
    def __init__(self, team):
        self.team = team
        self.user_profiles = None

    def get_user_avatar(self, slack, user_id):
        # lazy load profiles once
        if self.user_profiles is None:
            self.user_profiles = slack.api_call('users.list')['members']

        for user in self.user_profiles:
            if user['id'] == user_id:
                return user['profile']['image_192']

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
        user_ids = team_report.keys()
        random.shuffle(user_ids)
        for user_id in user_ids:
            data = team_report[user_id]
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
                'thumb_url': self.get_user_avatar(slack, user_id),
                'ts': calendar.timegm(data['reported_at'].timetuple()),
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
    """Checks reports statuses."""
    def is_weekend(self, today):
        return today.isoweekday() in (6, 7)

    def is_holiday(self, bot, today):
        return today in bot.plugin_config.get('holidays', {})

    def is_reportable(self, bot, today):
        is_weekend = self.is_weekend(today)
        is_holiday = self.is_holiday(bot, today)
        return not is_weekend and not is_holiday

    def is_time_to_send_summary(self, bot, report_by):
        tz = dateutil.tz.gettz(bot.plugin_config['timezone'])
        report_by = dateutil.parser.parse(report_by).replace(tzinfo=tz)
        now = datetime.now(dateutil.tz.tzlocal())
        return now >= report_by

    def is_too_early_to_ask(self, bot, ask_earliest):
        tz = dateutil.tz.gettz(bot.plugin_config['timezone'])
        ask_earliest = dateutil.parser.parse(ask_earliest).replace(tzinfo=tz)
        now = datetime.now(dateutil.tz.tzlocal())
        return now < ask_earliest

    def init_empty_report(self, bot, team_config):
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
                report[today][team] = self.init_empty_report(bot, team_config)

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

            is_reportable = self.is_reportable(bot, today)
            if not is_reportable:
                logging.debug('Today is not reportable (weekend or holiday)')

                report_holiday = (
                    self.is_holiday(bot, today) and
                    not self.is_too_early_to_ask(
                        bot, team_config['ask_earliest']
                    )
                )
                if report_holiday:
                    team_report['reported_at'] = datetime.utcnow()
                    holiday = bot.plugin_config.get('holidays', []).get(today)
                    bot.fast_queue.append(
                        SendMessage(
                            to=team_config['post_summary_to'],
                            text='\n'.join([
                                'No Standup Today :tada:',
                                holiday
                            ])
                        )
                    )
                continue

            if self.is_time_to_send_summary(bot, team_config['report_by']):
                logging.debug('It is time to send summary for {}'.format(team))
                bot.fast_queue.append(SendReportSummary(team))
                continue

            if self.is_too_early_to_ask(bot, team_config['ask_earliest']):
                logging.debug('Too early to ask people on {}'.format(team))
                continue

            for user_id in team_report.keys():

                if team_report[user_id].get('reported_at'):
                    continue

                bot.fast_queue.append(
                    AskStatus(teams=teams_by_user[user_id], user_id=user_id)
                )


class AskStatus(Task):
    """Asks a single user their status."""
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
    """Reads a single message."""
    def __init__(self, data):
        self.data = data

    def is_direct_message(self, bot):
        """Checks if this is a direct message."""
        return all([
            self.data.get('type', None) == 'message',
            'user' in self.data,
            'subtype' not in self.data,
            any([
                im['id'] == self.data['channel']
                for im in bot.storage.get('ims')
            ])
        ])

    def is_bot_message(self):
        """Checks if it is a bot message."""
        return 'bot_id' in self.data

    def is_hidden_message(self):
        """Checks if it is a hidden message."""
        return self.data.get('hidden', False)

    def is_message_edit(self):
        return self.data.get('subtype', None) == 'message_changed'

    def execute(self, bot, slack):
        logging.debug(u'Message event "{}"'.format(self.data))

        if self.is_hidden_message():
            if self.is_message_edit():
                bot.fast_queue.append(
                    ReadMessageEdit(self.data)
                )

        if self.is_bot_message():
            return

        if self.is_direct_message(bot):
            # in direct messages we only expect status messages
            bot.fast_queue.append(
                ReadStatusMessage(self.data)
            )


class ReadMessageEdit(ReadMessage):
    """Reads a message edit."""
    def execute(self, bot, slack):
        new_message = self.data['message']
        previous_message = self.data['previous_message']
        user_id = new_message['user']

        # see if we have previous message as report and propagate the edit
        today = datetime.utcnow().date()
        report = bot.storage.get('report')
        teams = bot.plugin_config['active_teams']

        for team in teams:
            # assume everything: report does not exist, team has not yet
            # reported today, user is not a part of the team in question
            user_report = report.get(today, {}).get(team, {}).get(user_id, {})
            if not user_report:
                continue

            if previous_message['text'] in user_report['report']:
                msg_idx = user_report['report'].index(previous_message['text'])
                user_report['report'][msg_idx] = new_message['text']
                user_report['edited_at'] = datetime.utcnow()
                logging.info('Applied message edit for {} on {}'.format(
                    user_id, team))


class ReadStatusMessage(ReadMessage):
    """Reads a status report from a user."""
    def execute(self, bot, slack):
        user_id = self.data['user']

        # check if there are any active context for this user
        teams = bot.get_user_lock(user_id)
        if teams is None:
            logging.debug(
                'User {} is not known to have any active context'.format(
                    user_id
                )
            )
            return

        # update status
        today = datetime.utcnow().date()
        report, is_first_line = bot.storage.get('report'), False
        for team in teams:
            user_report = report[today][team][user_id]
            user_report['reported_at'] = datetime.utcnow()
            is_first_line = len(user_report['report']) == 0
            user_report['report'].append(self.data['text'])

        # give user extra 5 minutes to add more lines in context of this lock
        bot.lock_user(user_id, teams, expire_in=300)
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
