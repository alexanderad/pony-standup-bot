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

        pretty_data = pprint.pformat({
            key: value for key, value in self._data.items()
            if key not in ['ims', 'users']
        }, indent=4)
        logging.info(pretty_data)
        logging.info('Flushed db to disk')

    def load(self):
        if not os.path.exists(self._file_name):
            return dict()

        with open(self._file_name, 'rb') as f:
            logging.info('Loaded db from disk')
            return pickle.load(f)
