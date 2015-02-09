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

    def tok(self,s):
        return tokenstream(resetable(iter(s)))

    def tok_exact(self,s):
        return tokenstream(resetable(iter(s)), state=StreamState.middle)

    def setUp(self):
        # called each time a test is run
        pass

    def test_identitity_cs(self):
        self.assertEqual(ControlSequence("x"), ControlSequence("x"))
        self.assertEqual(TokenCode('a', CatCode.letter), TokenCode('a', CatCode.letter))

    def test_match_prefix(self):
        rs = resetable(iter([1,2,3,4]))
        self.assertTrue(match_prefix(iter([1,2,3]), rs))
        # resets the stream in any case
        self.assertEqual([1,2,3,4], list(rs))

        rs = resetable(iter([1,2,3,4]))
        self.assertFalse (match_prefix(iter([4,2,3]), rs))
        self.assertEqual([1,2,3,4], list(rs))


    def test_control_sequence(self):
        t = defaultcatcode_table
        s = iter('\macro')
        r = control_sequence(resetable(s), t)
        self.assertEqual('macro',r)

        with self.assertRaises(TeXException):
            control_sequence(resetable(iter('macro')), t)

        with self.assertRaises(TeXException):
            control_sequence(resetable(iter('\\')), t)

        r = control_sequence(resetable(iter('\=')), t)
        self.assertEqual('=',r)

        r = control_sequence(resetable(iter('\~')), t)
        self.assertEqual('~',r)

        # TODO: need to check what TeX does in this case
        r = control_sequence(resetable(iter("\\\n")), t)
        self.assertEqual('',r)

    def test_tokenizer_text(self):
        text = 'text'
        s = resetable(iter(text))
        e = [ TokenCode(x, CatCode.letter) for x in iter(text) ]
        t = list(tokenstream(s))
        self.assertEqual(t, e)

        s = resetable(self.tok('\macro'))
        self.assertEqual(list(s), [ControlSequence('macro')])

        s = resetable(self.tok('\par'))
        self.assertEqual(list(s), [ControlSequence('par')])


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

    def test_handle_def(self):
        s = resetable(self.tok('\macro#1{#1}'))
        m = {}
        handle_def(s,m)
        self.assertEqual(m['macro'], ([[],[]], list(self.tok('#1'))))


    def test_match_macro_patter(self):
        pattern = read_params(resetable(self.tok('x{')))
        tokens = self.tok('x')
        res = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [])

        pattern = read_params(resetable(self.tok('x{')))
        tokens = self.tok('y')
        with self.assertRaises(TeXMatchError):
            res = match_macro_pattern(pattern,tokens)

        pattern = read_params(resetable(self.tok('#1{')))
        tokens = self.tok('x')
        res = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('x'))])

        pattern = read_params(resetable(self.tok('#1{')))
        tokens = self.tok('{x}')
        res = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('x'))])

        pattern = read_params(resetable(self.tok('#1 delimiter {')))
        tokens = self.tok(' match result delimiter ')
        res = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok(' match result'))])

        pattern = read_params(resetable(self.tok('#1 delimiter {')))
        tokens = self.tok(' match {result delimiter ')
        res = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok(' match {result'))])

        pattern = read_params(resetable(self.tok('#1#2{')))
        tokens = self.tok('xy')
        res = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('x')), list(self.tok('y'))])

        pattern = read_params(resetable(self.tok('p#1d{')))
        tokens = self.tok('p{he{ll}o}dxd2 some text \par')
        res = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('{he{ll}o}'))])

        pattern = read_params(resetable(self.tok('p#1d#2d2{')))
        tokens = self.tok('p{he{ll}o}dxd2 some text \par')
        res = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res),
                [list(self.tok('{he{ll}o}')),
                 list(self.tok('x')) ])

        pattern = read_params(resetable(self.tok('p#1d#2d2#3\par{')))
        tokens = self.tok('p{he{ll}o}dxd2 some text \par')
        res = match_macro_pattern(pattern,tokens)
        self.assertEqual(
                list(res),
                [list(self.tok('{he{ll}o}')),
                 list(self.tok('x')),
                 list(self.tok_exact(' some text '))])

    def test_expand_params(self):
        body = list(self.tok('#1'))
        par = list(self.tok('param'))
        res = expand_params(body, [par])
        self.assertEqual(res, list(self.tok('param')))

        with self.assertRaises(TeXException):
            body = list(self.tok('#'))
            par = list(self.tok('param'))
            res = expand_params(body, [par])

        body = list(self.tok('{#1} \z{#1#3}#1'))
        par = [self.tok('a'), self.tok('b'),
               self.tok('c'), self.tok('d')]
        par = [list(x) for x in par]
        res = expand_params(body, par)
        self.assertEqual(res, list(self.tok('{a} \z{ac}a')))


    def test_expand(self):
        s = resetable(self.tok('\def\macro#1{#1 #1}'))
        b = expand(s)
        self.assertEqual(list(b), list(self.tok('')))

        s = resetable(self.tok('\def\macro#1{#1 #1}\macro{Hello}'))
        b = expand(s)
        self.assertEqual(list(b), list(self.tok('Hello Hello')))

        s = resetable(self.tok('\def\macro#1{#1 #1}\\unknownmacro{Hello}'))
        b = expand(s)
        self.assertEqual(list(b), list(self.tok('\\unknownmacro{Hello}')))

        s = resetable(self.tok('\def\macro#1{#1 #1}\\unknownmacro{\macro{Hello}}'))
        b = expand(s)
        self.assertEqual(list(b), list(self.tok('\\unknownmacro{Hello Hello}')))


if __name__ == '__main__':
    unittest.main()

