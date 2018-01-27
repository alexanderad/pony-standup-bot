import os
import time
import logging
import logging.handlers

from slackclient import SlackClient

from .tasks_queue import TasksQueue


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
        self.log.debug('Received pong: {}'.format(data))

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
        self.log.info('Gracefully stopping now')
