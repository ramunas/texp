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

    def test_next_token_or_group(self):
        s = tokenstream(resetable(iter('{group}')))
        group = next_token_or_group(s)
        res = list(tokenstream(resetable(iter('group'))))
        self.assertEqual(res, list(group))

        s = tokenstream(resetable(iter('g')))
        group = next_token_or_group(s)
        res = list(tokenstream(resetable(iter('g'))))
        self.assertEqual(res, list(group))


    def tok(self,s):
        return tokenstream(resetable(iter(s)))

    def test_read_params(self):
        s = resetable(self.tok('#1{'))
        args = read_params(s)
        self.assertEqual([[],[]], args)

        s = resetable(self.tok('#1delim{'))
        args = read_params(s)
        self.assertEqual([[],list(self.tok('delim'))], args)

        s = resetable(self.tok('#1#2{'))
        args = read_params(s)
        self.assertEqual([[],[],[]], args)

        s = resetable(self.tok('#1#3{'))
        with self.assertRaises(TeXException):
            args = read_params(s)

        s = resetable(self.tok('pref#1delim1#2delim2{'))
        args = read_params(s)
        tk = lambda s: list(self.tok(s))
        self.assertEqual([tk('pref'),tk('delim1'),tk('delim2')], args)


    def test_find_params(self):
        p = find_params(self.tok('#1 #2 {#3} #1'))
        self.assertEqual(list(p), [TokenCode(x, CatCode.other) for x in ['1','2','3','1']])

    def test_find_highest_param(self):
        h = find_highest_param(self.tok('#1 #2 {#3} #1'))
        self.assertEqual(h, 3)

    def test_read_body(self):
        t = "body #1 \\text{#2} #3"
        s1 = resetable(self.tok("{%s}" % t))
        s2 = self.tok(t)
        b = read_body(s1)
        self.assertEqual(list(b), list(s2))

    def test_def(self):
        s = resetable(self.tok("\\name#1#2#3{#1#2#3}"))
        (n,p,b) = read_def(s)
        self.assertEqual(n.name, "name")
        self.assertEqual([[],[],[],[]], p)
        self.assertEqual(list(b), list(self.tok("#1#2#3")))

        s = resetable(self.tok("\\name#1#2#3{#1#2#4#3}"))
        with self.assertRaises(TeXException):
            (n,p,b) = read_def(s)

    def test_match_macro_pattern(self):
        pass



if __name__ == '__main__':
    unittest.main()

