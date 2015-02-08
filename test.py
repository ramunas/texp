#!/usr/bin/env python3
import unittest
from texp import *

class TestTeX(unittest.TestCase):

    def setUp(self):
        # called each time a test is run
        pass

    def test_identitity_cs(self):
        self.assertEqual(ControlSequence("x"), ControlSequence("x"))
        self.assertEqual(TokenCode('a', CatCode.letter), TokenCode('a', CatCode.letter))
        self.assertEqual(ParamToken(1), ParamToken(1))

    def test_match_prefix(self):
        rs = resetable(iter([1,2,3,4]))
        self.assertTrue(match_prefix(iter([1,2,3]), rs))
        # resets the stream in any case
        self.assertEqual([1,2,3,4], list(rs))

        rs = resetable(iter([1,2,3,4]))
        self.assertFalse (match_prefix(iter([4,2,3]), rs))
        self.assertEqual([1,2,3,4], list(rs))

if __name__ == '__main__':
    unittest.main()
