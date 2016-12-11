import freezegun
import unittest
from datetime import datetime, timedelta

import pony.storage


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.storage = pony.storage.Storage('_dummy_file')

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
