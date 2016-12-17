# coding=utf-8
import os
import pickle
import pprint
import threading
import logging

from datetime import datetime, timedelta


class Storage(object):
    """Simple key value storage."""
    def __init__(self, file_name=None):
        self._lock = threading.Lock()
        self._file_name = file_name
        self._data = self.load()

        # get or set expiration dictionary
        if self._data.get('_expire') is None:
            self._data['_expire'] = dict()

    def set(self, key, value, expire_in=None):
        with self._lock:
            self._data[key] = value
            if expire_in is not None:
                self._data['_expire'][key] = datetime.utcnow() + timedelta(
                    seconds=expire_in)

    def unset(self, key):
        with self._lock:
            del self._data[key]
            if key in self._data['_expire']:
                del self._data['_expire'][key]

    def get(self, key, default=None):
        with self._lock:
            is_expired_key = (
                key in self._data['_expire']
                and datetime.utcnow() > self._data['_expire'][key]
            )
            if is_expired_key:
                del self._data[key]
                del self._data['_expire'][key]

            if key not in self._data and default is not None:
                self._data[key] = default

            return self._data.get(key)

    def save(self):
        with open(self._file_name, 'wb') as f:
            pickle.dump(self._data, f)

        pretty_data = pprint.pformat({
            key: value for key, value in self._data.items()
            if key not in ['ims', 'users']
        }, indent=4)
        logging.info(pretty_data)
        logging.debug('Flushed db to disk')

    def load(self):
        if not os.path.exists(self._file_name):
            return dict()

        with open(self._file_name, 'rb') as f:
            logging.info('Loaded db from disk')
            return pickle.load(f)
