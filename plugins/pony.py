import os
import threading
import pickle
import pprint
import random
import logging
import collections
import dateutil.tz
import dateutil.parser

from datetime import datetime, timedelta

from rtmbot.core import Plugin, Job


class WorldTick(Job):
    """World tick."""
    def __init__(self, bot, queue, interval):
        super(WorldTick, self).__init__(interval)
        self.bot = bot
        self.queue = queue

    def run(self, slack):
        visible_tasks = len(self.queue)

        for x in range(visible_tasks):
            task = self.queue.popleft()
            task.execute(bot=self.bot, slack=slack)

        return []


class Task(object):
    def execute(self, bot, slack):
        pass


class SendMessageTask(Task):
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


class ReportStatusTask(Task):
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
        not_seen_online = []
        for user_id, status in team_report.items():
            user_data = bot.get_user_by_id(user_id)
            if not user_data:
                continue

            full_name = user_data['profile'].get('real_name')
            color = '#{}'.format(user_data.get('color'))

            if not status['seen_online']:
                not_seen_online.append(full_name)
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
                'text': '\n'.join(status['report'])[:1024]
            })

        if not_seen_online:
            reports.append({
                'color': '#f2f2f2',
                'title': 'Offline today',
                'text': ', '.join(not_seen_online)
            })

        if reports:
            channel = team_config['post_summary_to']
            bot.fast_queue.append(
                SendMessageTask(
                    to=channel,
                    text='Standup Summary for Today',
                    attachments=reports
                )
            )

            team_report['reported_at'] = datetime.utcnow()

            logging.info('Reported status for team {}'.format(self.team))

        bot.fast_queue.append(UnlockUsersTask(team=self.team))


class UnlockUsersTask(Task):
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


class CheckReportsTask(Task):
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
        bot.slow_queue.append(CheckReportsTask())

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
                bot.fast_queue.append(ReportStatusTask(team))
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
                    AskStatusTask(team=team, user_id=user_id)
                )


class AskStatusTask(Task):
    PHRASES = (
        'Hey, just wanted to ask your current status for {}, how it is going?',
        'Psst. I know, you hate it. But I have to ask. Any blockers on {}?',

        "Hi. Ponies don't have to report. People on {} made us "
        "to ask other people to. How are you doing today?",

        "Amazing day, dear. I'm gathering status update for {}. How it "
        "is going?",

        "Hello, it's me again. How are you doing today? {} will be excited "
        "to hear. I needs few words from you.",

        "Heya. Just asked all our {} members. You are the last one. How's "
        "your day?",

        "Dear, sorry for disturbing you. Would you mind sharing your status "
        "with {}? Few words.",

        "Good morning. Your beloved pony is here again to ask your daily "
        "status. How are you doing today?"
    )

    def __init__(self, team, user_id):
        self.team = team
        self.user_id = user_id

    def execute(self, bot, slack):
        team_data = bot.plugin_config[self.team]

        if not bot.is_online(self.user_id):
            logging.info(
                'User {} is not online, skipping'.format(self.user_id))
            return

        if bot.get_user_lock(self.user_id):
            logging.info(
                'User {} is already locked, skipping'.format(self.user_id))
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
            SendMessageTask(
                to=self.user_id,
                text=random.choice(self.PHRASES).format(team_data['name'])
            )
        )


class ReadMessageTask(Task):
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

        logging.info('User {} says "{}"'.format(user_id, self.data['text']))

        # give user extra 10 seconds to add more lines
        bot.lock_user(user_id, team, expire_in=10)
        if is_first_line:
            bot.fast_queue.append(
                SendMessageTask(to=user_id, text='Thanks! :+1:')
            )
        else:
            bot.fast_queue.append(
                SendMessageTask(to=user_id, text="Ok, I'll add that too.")
            )


class FlushDBTask(Task):
    def execute(self, bot, slack):
        logging.debug('Saving data')
        bot.storage.save()
        bot.slow_queue.append(FlushDBTask())


class Storage(object):
    """Simple key value storage."""
    def __init__(self, file_name=None):
        self._file_name = file_name
        self._data = self.load()
        self._ts = dict()
        self._lock = threading.Lock()

    def set(self, key, value, expire_in=None):
        with self._lock:
            self._data[key] = value
            if expire_in is not None:
                self._ts[key] = datetime.utcnow() + timedelta(seconds=expire_in)

    def unset(self, key):
        with self._lock:
            del self._data[key]
            if key in self._ts:
                del self._ts[key]

    def get(self, key, default=None):
        with self._lock:
            if key in self._ts and datetime.utcnow() > self._ts[key]:
                del self._data[key]
                del self._ts[key]

            if key not in self._data and default is not None:
               self._data[key] = default

            return self._data.get(key)

    def save(self):
        with open(self._file_name, 'wb') as f:
            pickle.dump(self._data, f)

        logging.debug('Saved db to disk')

        pretty_data = pprint.pformat({
            key: value for key, value in self._data.items()
            if key not in ['ims', 'users']
        }, indent=4)
        logging.debug(pretty_data)

    def load(self):
        if not os.path.exists(self._file_name):
            return dict()

        with open(self._file_name, 'rb') as f:
            logging.info('Loaded db from disk')
            return pickle.load(f)


class StandupPonyPlugin(Plugin):
    """Standup Pony plugin."""
    def __init__(self, name=None, slack_client=None, plugin_config=None):
        super(StandupPonyPlugin, self).__init__(
            name, slack_client, plugin_config)
        self.slow_queue = collections.deque()
        self.fast_queue = collections.deque()

        self.storage = Storage(plugin_config.get('db_file'))

        # world updates
        self.slow_queue.append(UpdateUserList())
        self.slow_queue.append(UpdateIMList())
        self.slow_queue.append(CheckReportsTask())
        self.slow_queue.append(FlushDBTask())

    def get_channel(self, channel_id):
        channels = self.storage.get('channels', dict())

        if channel_id not in channels:
            channels[channel_id] = self.slack_client.api_call()
            self.storage.set('channels', channels)

        return channels[channel_id]

    def get_user_by_id(self, user_id):
        users = self.storage.get('users')
        for user in users:
            if user['id'] == user_id:
                return user

    def get_user_by_name(self, user_name):
        user_name = user_name.strip('@')
        users = self.storage.get('users')
        for user in users:
            if user['name'] == user_name:
                return user

    def is_online(self, user_id):
        data = self.slack_client.api_call('users.getPresence', user=user_id)
        if data['ok']:
            return data['presence'] == 'active'

        return False

    def lock_user(self, user_id, team, expire_in):
        lock_key = '{}_lock'.format(user_id)
        self.storage.set(lock_key, team, expire_in=expire_in)
        logging.info('Locked user {} for {} sec'.format(user_id, expire_in))

    def unlock_user(self, user_id):
        lock_key = '{}_lock'.format(user_id)
        self.storage.unset(lock_key)
        logging.info('Unlocked user {}'.format(user_id))

    def get_user_lock(self, user_id):
        lock_key = '{}_lock'.format(user_id)
        return self.storage.get(lock_key)

    def process_message(self, data):
        self.fast_queue.append(ReadMessageTask(data=data))

    def process_im_created(self, data):
        self.fast_queue.append(UpdateIMList())

    def register_jobs(self):
        # slow queue
        self.jobs.append(
            WorldTick(
                bot=self,
                queue=self.slow_queue,
                interval=60
            )
        )
        logging.debug('Registered slow queue')

        # fast queue
        self.jobs.append(
            WorldTick(
                bot=self,
                queue=self.fast_queue,
                interval=0.75
            )
        )
        logging.debug('Registered fast queue')
