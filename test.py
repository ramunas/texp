#!/usr/bin/env python3
import unittest
from texp import *

class TestResetableStream(unittest.TestCase):

    def test_resetable1(self):
        x = [1,2,3]
        s = resetable(iter(x))
        s.__enter__()
        list(s)
        s.__reset__()
        self.assertEqual(x, list(s))

    def test_resetable2(self):
        x = [1,2,3]
        s = resetable(iter(x))
        list(s)
        self.assertNotEqual(x, list(s))

    def test_resetable3(self):
        x = [1,2,3]
        s = resetable(iter(x))
        with s:
            list(s)
        self.assertEqual(x, list(s))

    def test_resetable4(self):
        x = [1,2,3]
        s = resetable(iter(x))
        with s:
            with s:
                list(s)
            list(s)
        self.assertEqual(x, list(s))

    def test_resetable_peak(self):
        x = [1,2,3]
        s = resetable(iter(x))
        self.assertEqual(peak(s), 1)
        self.assertEqual(list(s),x)


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

    def test_tokenizer_text(self):
        text = 'text'
        s = resetable(iter(text))
        e = [ TokenCode(x, CatCode.letter) for x in iter(text) ]
        t = list(tokenstream(s))
        self.assertEqual(t, e)

    def test_tokenizer_macro(self):
        text = '\macro  x'
        s = resetable(iter(text))
        t = list(tokenstream(s))
        e = [ControlSequence('macro'), TokenCode('x', CatCode.letter)]
        self.assertEqual(t, e)

    def test_next_group(self):
        s = tokenstream(resetable(iter('group}')))
        group = next_group(s)
        res = list(tokenstream(resetable(iter('group'))))
        self.assertEqual(res, list(group))

        s = tokenstream(resetable(iter('{group}')))
        with self.assertRaises(StopIteration):
            group = next_group(s)


if __name__ == '__main__':
    unittest.main()

