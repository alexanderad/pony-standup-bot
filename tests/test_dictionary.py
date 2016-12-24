from __future__ import absolute_import

import freezegun
import unittest

from pony.dictionary import Dictionary


class DictionaryTest(unittest.TestCase):
    def test_initial_seed_is_predictable(self):
        self.assertEqual(
            Dictionary.initial_seed('A123'),
            Dictionary.initial_seed('A123')
        )

    def test_initial_seed_eats_slack_user_ids(self):
        self.assertEqual(Dictionary.initial_seed('U023BECGF'), 199)
        self.assertEqual(Dictionary.initial_seed('U04RVVBAY'), 290)

    def test_pick_depends_on_user_id(self):
        self.assertNotEqual(
            Dictionary.pick(Dictionary.THANKS, 'U023BECGF'),
            Dictionary.pick(Dictionary.THANKS, 'U04RVVBAY'),
        )

    def test_pick_is_stable(self):
        self.assertEqual(
            Dictionary.pick(Dictionary.THANKS, 'U023BECGF'),
            Dictionary.pick(Dictionary.THANKS, 'U023BECGF'),
        )

    def test_pick_depends_on_day_of_the_year(self):
        with freezegun.freeze_time('2016-01-01'):
            day1_phrase = Dictionary.pick(Dictionary.THANKS, 'U023BECGF')

        with freezegun.freeze_time('2016-01-02'):
            day2_phrase = Dictionary.pick(Dictionary.THANKS, 'U023BECGF')

        self.assertNotEqual(day1_phrase, day2_phrase)
