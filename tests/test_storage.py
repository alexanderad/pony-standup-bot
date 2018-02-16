from __future__ import absolute_import

import os
import contextlib
import freezegun
import tempfile
import random
import unittest
from datetime import datetime, timedelta

import pony.storage


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.storage = pony.storage.Storage('_dummy_file')

    @contextlib.contextmanager
    def temp_file(self):
        f = os.path.join(tempfile.gettempdir(), str(random.random()))
        try:
            yield f
        finally:
            os.remove(f)

    def test_set_get(self):
        self.storage.set('_key', '_test_value')
        self.assertEqual(self.storage.get('_key'), '_test_value')

    def test_set_expires(self):
        self.storage.set('_key', '_test_value', expire_in=10)
        self.assertEqual(self.storage.get('_key'), '_test_value')

        with freezegun.freeze_time(datetime.utcnow() + timedelta(seconds=15)):
            self.assertIsNone(self.storage.get('_key'))

    def test_unset(self):
        self.storage.set('_key', '_test_value')
        self.storage.unset('_key')
        self.assertIsNone(self.storage.get('_key'))

    def test_get_with_default_sets(self):
        self.storage.get('_key', default='_test_value')
        self.assertEqual(self.storage.get('_key'), '_test_value')

    def test_load_save(self):
        with self.temp_file() as storage_file:
            self.storage = pony.storage.Storage(storage_file)
            self.storage.set('test_key', 'test_value')
            self.storage.save()

            self.storage = pony.storage.Storage(storage_file)
            self.assertEqual(self.storage.get('test_key'), 'test_value')

    def test_load_save_respects_expiration(self):
        with self.temp_file() as storage_file:
            self.storage = pony.storage.Storage(storage_file)
            self.storage.set('test_key', 'test_value', expire_in=10)
            self.storage.set('test_key_2', 'test_value')
            self.storage.save()

            with freezegun.freeze_time(
                    datetime.utcnow() + timedelta(seconds=15)):
                self.storage = pony.storage.Storage(storage_file)
                self.assertIsNone(self.storage.get('test_key'))
                self.assertEqual(self.storage.get('test_key_2'), 'test_value')
