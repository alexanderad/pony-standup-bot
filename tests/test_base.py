from __future__ import absolute_import

import unittest

from pony.pony import Pony


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.config = dict(
            pony=dict(
                db_file='test.db',
                log_file='test.log',
                debug=True,
            ),
            slack=dict(
                token='_slack_token'
            )
        )
        self.bot = Pony(config=self.config)
