# coding=utf-8
import time
import logging
import collections

from rtmbot.core import Plugin

import tasks
from .jobs import WorldTick
from .storage import Storage


class StandupPonyPlugin(Plugin):
    """Standup Pony plugin."""
    def __init__(self, name=None, slack_client=None, plugin_config=None):
        super(StandupPonyPlugin, self).__init__(
            name, slack_client, plugin_config)
        self.slow_queue = collections.deque()
        self.fast_queue = collections.deque()

        self.storage = Storage(plugin_config.get('db_file'))

        # world updates
        self.slow_queue.append(tasks.UpdateUserList())
        self.slow_queue.append(tasks.UpdateIMList())
        self.slow_queue.append(tasks.CheckReports())
        self.slow_queue.append(tasks.SyncDB())

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

    def user_is_online(self, user_id):
        user = self.get_user_by_id(user_id)
        if user is not None and user.get('presence') == 'active':
            return True

        return False

    def send_typing(self, to, over_time=1.25):
        time.sleep(over_time * 0.25)
        self.slack_client.server.send_to_websocket(
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

    def register_jobs(self):
        # slow queue, some minutes between runs (slow world queue)
        self.jobs.append(
            WorldTick(
                bot=self,
                queue=self.slow_queue,
                interval=2 * 60
            )
        )
        logging.info('Registered slow queue')

        # fast queue, super small delay before tasks flushed (fast world queue)
        self.jobs.append(
            WorldTick(
                bot=self,
                queue=self.fast_queue,
                interval=0.5
            )
        )
        logging.info('Registered fast queue')
