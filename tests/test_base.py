from __future__ import absolute_import

import unittest
from flexmock import flexmock

from pony.pony import StandupPonyPlugin


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.bot = StandupPonyPlugin(
            plugin_config={
                'db_file': ''
            },
            slack_client=flexmock(server=flexmock())
        )
        self.slack = flexmock()
