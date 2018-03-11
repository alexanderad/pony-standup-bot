import os
import time
import logging
import logging.handlers

from slackclient import SlackClient

from pony import tasks
from pony.storage import Storage
from pony.tasks_queue import TasksQueue
from pony.models.base import DatabaseConnectionManager


class Bot(object):
    PING_INTERVAL_SECONDS = 5

    def __init__(self, config):
        self.config = config
        self.work_dir = config['pony'].get('work_dir') or os.getcwd()
        self.debug = config['pony']['debug']
        self.log = self.setup_logging()
        self.slack = SlackClient(config['slack']['token'])
        self.last_ping_at = time.time()

        # slow queue, some minutes between runs (slow world queue)
        self.slow_queue = TasksQueue(self, interval=5)
        # fast queue, super small delay before tasks flushed (fast world queue)
        self.fast_queue = TasksQueue(self, interval=0.5)

    def setup_logging(self):
        log = logging.getLogger('pony')

        if self.debug:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)

        log_file = os.path.join(
            self.work_dir, self.config['pony']['log_file'])
        log_max_size_mb = self.config['pony'].get('log_max_size_mb', 10)
        log_max_files = self.config['pony'].get('log_max_files', 5)

        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=log_max_size_mb * 1024 * 1024,
            backupCount=log_max_files,
            encoding='utf-8',
        )
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        log.addHandler(handler)

        return log

    def connect(self):
        self.log.info('Connecting...')
        return self.slack.rtm_connect()

    def reconnect(self):
        self.log.info('Attempting to reconnect...')
        return self.connect()

    def ping(self):
        now = time.time()
        if now - self.last_ping_at > self.PING_INTERVAL_SECONDS:
            self.slack.server.ping()
            self.last_ping_at = now

    def process_messages(self):
        for message in self.slack.rtm_read():
            message_type = message.get('type')
            handler = 'process_{}'.format(message_type)
            if not hasattr(self, handler):
                continue

            try:
                getattr(self, handler)(message)
            except Exception as e:
                self.log.error(
                    'Error in handler {} '
                    'processing message {}\n{}'.format(
                        handler, message, e
                    ))

                if self.debug:
                    raise

    def process_hello(self, data):
        self.log.info('Successfully connected: {}'.format(data))

    def process_pong(self, data):
        self.log.debug('Received pong message: {}'.format(data))

    def process_goodbye(self, data):
        self.log.info('Received goodbye message: {}'.format(data))
        self.reconnect()

    def process_tasks(self):
        for queue in (self.slow_queue, self.fast_queue):
            queue.process()

    def start(self):
        self.log.info('Initialized at {}'.format(self.work_dir))
        self.connect()

        while True:
            self.process_messages()
            self.process_tasks()
            self.ping()
            time.sleep(0.1)

    def stop_gracefully(self):
        DatabaseConnectionManager.close()
        self.log.info('Gracefully stopping')


class Pony(Bot):

    def __init__(self, config):
        super(Pony, self).__init__(config)

        DatabaseConnectionManager.initialize(self.config['pony'])

        db_file = os.path.join(self.work_dir, self.config['pony']['db_file'])
        self.storage = Storage(db_file)

        # world updates
        self.slow_queue.append(tasks.UpdateUserList())
        self.slow_queue.append(tasks.UpdateIMList())
        self.slow_queue.append(tasks.CheckReports())
        self.slow_queue.append(tasks.SyncDB())

    def get_channel(self, channel_id):
        channels = self.storage.get('channels', dict())

        if channel_id not in channels:
            channels[channel_id] = self.slack.api_call()
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

    def user_is_online(self, user_id):
        user = self.get_user_by_id(user_id)
        if user is not None and user.get('presence') == 'active':
            return True

        return False

    def send_typing(self, to, over_time=1.25):
        time.sleep(over_time * 0.25)
        self.slack.server.send_to_websocket(
            dict(type='typing', channel=to))
        time.sleep(over_time * 0.75)

    def lock_user(self, user_id, teams, expire_in):
        lock_key = '{}_lock'.format(user_id)
        self.storage.set(lock_key, teams, expire_in=expire_in)
        logging.info('Locked user {} for {} sec'.format(user_id, expire_in))

    def get_user_lock(self, user_id):
        lock_key = '{}_lock'.format(user_id)
        return self.storage.get(lock_key)

    def process_message(self, data):
        self.fast_queue.append(tasks.ReadMessage(data=data))

    def process_im_created(self, data):
        self.fast_queue.append(tasks.UpdateIMList())

    def process_presence_change(self, data):
        self.fast_queue.append(tasks.ProcessPresenceChange(
            data.get('user'), data.get('presence')))
