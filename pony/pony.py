# coding=utf-8
import os
import time
import logging
import logging.handlers

import tasks
from .bot import Bot
from .storage import Storage


class Pony(Bot):

    def __init__(self, config):
        super(Pony, self).__init__(config)

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
