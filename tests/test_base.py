from __future__ import absolute_import

from datetime import date

import unittest

from pony.bot import Pony


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.config = dict(
            pony=dict(
                db_file='test.db',
                log_file='test.log',
                debug=True,
                timezone='UTC',
                last_call='5 minutes'
            ),
            holidays={
                date(2016, 12, 1): 'Romanian National Day'
            },
            slack=dict(
                token='_slack_token'
            )
        )
        self.bot = Pony(config=self.config)
