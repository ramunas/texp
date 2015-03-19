#!/usr/bin/env python3
import unittest
import weakref
import gc
from texp import *


class TestOther(unittest.TestCase):
    def test_copytobuf(self):
        it = iter([1,2,3])
        buf = []
        s = copytobuf(buf, it)
        for i in s:
            pass
        self.assertEqual([1,2,3],buf)

        it = iter([1,2,3])
        buf = []
        s = copytobuf(buf, it)
        next(s)
        self.assertEqual([1],buf)

        self.assertEqual(2, next(it))
        self.assertEqual(3, next(it))
        with self.assertRaises(StopIteration):
            next(it)

    def test_copytoweakbuf(self):
        it = iter([1,2,3])
        buf = []
        b = lambda: buf
        s = copytoweakbuf(b, it)
        for i in s:
            pass
        self.assertEqual([1,2,3],buf)

        it = iter([1,2,3])
        buf = []
        b = lambda: buf
        s = copytoweakbuf(b, it)
        next(s)
        self.assertEqual([1],buf)
        self.assertEqual(2, next(it))
        self.assertEqual(3, next(it))
        with self.assertRaises(StopIteration):
            next(it)

        it = iter([1,2,3])
        buf = []
        b = lambda: buf
        s = copytoweakbuf(b, it)
        next(s)
        self.assertEqual([1],buf)
        buf = None
        self.assertEqual(b(), None)
        self.assertEqual(2, next(s))
        self.assertEqual(3, next(s))
        with self.assertRaises(StopIteration):
            next(s)

        # using weakreferences
        it = iter([1,2,3])
        class lst(list): pass
        buf = lst([])
        b = weakref.ref(buf)
        s = copytoweakbuf(b, it)
        next(s)
        del buf
        gc.collect()
        self.assertEqual(b(), None)
        self.assertEqual(2, next(s))
        self.assertEqual(3, next(s))
        with self.assertRaises(StopIteration):
            next(s)



class TestTeX(unittest.TestCase):

    def setUp(self):
        # called each time a test is run
        pass

    def tok(self,s):
        return tokenstream(iter(s))

    def tok_exact(self,s):
        return tokenstream(iter(s), state=StreamState.middle)

    def test_tokenstream_to_str(self):
        x = self.tok('hello')
        self.assertEqual(tokenstream_to_str(x), 'hello')

        x = self.tok('')
        self.assertEqual(tokenstream_to_str(x), '')

        with self.assertRaises(TeXException):
            tokenstream_to_str(self.tok('\hello'))


    def test_identitity_cs(self):
        self.assertEqual(control_sequence("x"), control_sequence("x"))
        self.assertEqual(token_code('a', CatCode.letter), token_code('a', CatCode.letter))

    def test_match_prefix(self):
        rs = iter([1,2,3,4])
        (s, res) = match_prefix(iter([1,2,3]), rs)
        self.assertTrue(res)
        self.assertEqual([4], list(s))

        rs = iter([1,2,3,4])
        (s, res) = match_prefix(iter([4,2,3]), rs)
        self.assertFalse(res)
        self.assertEqual([2,3,4], list(s))


    def test_read_control_sequence(self):
        state = StreamState.middle
        t = defaultcatcode_table
        s = iter('\macro')
        (s,st,r) = read_control_sequence(s, state, t)
        self.assertEqual('macro',r)

        with self.assertRaises(TeXException):
            read_control_sequence(iter('macro'), state, t)

        with self.assertRaises(TeXException):
            read_control_sequence(iter('\\'), state, t)

        r = read_control_sequence(iter('\='), state, t)
        self.assertEqual('=',r[2])

        r = read_control_sequence(iter('\~'), st, t)
        self.assertEqual('~',r[2])

        r = read_control_sequence(iter("\\\n"), st, t)
        self.assertEqual('',r[2])

    def test_tokenstream(self):
        # TODO: definitely better tests neede
        text = 'text'
        s = iter(text)
        e = [ token_code(x, CatCode.letter) for x in iter(text) ]
        t = list(tokenstream(s))
        self.assertEqual(t, e)

        s = self.tok('\macro')
        self.assertEqual(list(s), [control_sequence('macro')])

        s = self.tok('\macro h')
        self.assertEqual(list(s), [control_sequence('macro'), token_code('h', CatCode.letter)])

        s = self.tok('\par')
        self.assertEqual(list(s), [control_sequence('par')])

        s = self.tok("% aa\n")
        self.assertEqual(list(s), [])

        s = self.tok("% aa\n a")
        self.assertEqual(list(s), [token_code('a', CatCode.letter)])

        s = self.tok("x\n\nx")
        self.assertEqual(list(s), [token_code('x', CatCode.letter), token_code(' ', CatCode.space), control_sequence('par'), token_code('x', CatCode.letter)])


    def test_tokenizer_macro(self):
        text = '\macro  x'
        s = iter(text)
        t = list(tokenstream(s))
        e = [control_sequence('macro'), token_code('x', CatCode.letter)]
        self.assertEqual(t, e)

    def test_next_group(self):
        s = tokenstream(iter('group}'))
        (s,group) = next_group(s)
        res = list(tokenstream(iter('group')))
        self.assertEqual(res, list(group))

        s = tokenstream(iter('{group}'))
        with self.assertRaises(StopIteration):
            group = next_group(s)

    def test_next_token_or_group(self):
        s = tokenstream(iter(''))
        with self.assertRaises(StopIteration):
            list(next_token_or_group(s)[1])

        s = tokenstream(iter('{group}'))
        (s,group) = next_token_or_group(s)
        res = list(tokenstream(iter('group')))
        self.assertEqual(res, list(group))

        s = tokenstream(iter('g'))
        (s,group) = next_token_or_group(s)
        res = list(tokenstream(iter('g')))
        self.assertEqual(res, list(group))


    def test_read_params(self):
        s = self.tok('{')
        args = read_params(s)
        self.assertEqual([[]], args[1])

        s = self.tok('#1{')
        args = read_params(s)
        self.assertEqual([[],[]], args[1])

        s = self.tok('#1delim{')
        args = read_params(s)
        self.assertEqual([[],list(self.tok('delim'))], args[1])

        s = self.tok('#1#2{')
        args = read_params(s)
        self.assertEqual([[],[],[]], args[1])

        s = self.tok('#1#3{')
        with self.assertRaises(TeXMatchError):
            args = read_params(s)

        s = self.tok('#a{')
        with self.assertRaises(TeXMatchError):
            args = read_params(s)

        s = self.tok('#0{')
        with self.assertRaises(TeXMatchError):
            args = read_params(s)

        s = self.tok('pref#1delim1#2delim2{')
        args = read_params(s)
        tk = lambda s: list(self.tok(s))
        self.assertEqual([tk('pref'),tk('delim1'),tk('delim2')], args[1])


    def test_find_params(self):
        p = find_params(self.tok(''))
        self.assertEqual(list(p), [])

        p = find_params(self.tok('some text'))
        self.assertEqual(list(p), [])

        p = find_params(self.tok('#1 #2 {#3} #1'))
        self.assertEqual(list(p), [token_code(x, CatCode.other) for x in ['1','2','3','1']])

    def test_find_highest_param(self):
        h = find_highest_param(self.tok(''))
        self.assertEqual(h, None)

        h = find_highest_param(self.tok('some text'))
        self.assertEqual(h, None)

        h = find_highest_param(self.tok('#1 #2 {#3} #1'))
        self.assertEqual(h, 3)

    def test_read_body(self):
        t = "body #1 \\text{#2} #3"
        s1 = self.tok("{%s}" % t)
        s2 = self.tok(t)
        (s,b) = read_body(s1)
        self.assertEqual(list(b), list(s2))

    def test_read_def(self):
        s = self.tok("\\name{}")
        (s, n,p,b) = read_def(s)
        self.assertEqual(n.name, "name")
        self.assertEqual([[]], p)
        self.assertEqual(list(b), list(self.tok('')))

        s = self.tok("\\name#1#2#3{#1#2#3}")
        (s, n,p,b) = read_def(s)
        self.assertEqual(n.name, "name")
        self.assertEqual([[],[],[],[]], p)
        self.assertEqual(list(b), list(self.tok("#1#2#3")))

        s = self.tok("\\macro{#0}")
        with self.assertRaises(TeXException):
            (s, n,p,b) = read_def(s)

        s = self.tok("\\macro{#1}")
        with self.assertRaises(TeXException):
            (s, n,p,b) = read_def(s)

        s = self.tok("\\name#1#2#3{#1#2#4#3}")
        with self.assertRaises(TeXException):
            (s, n,p,b) = read_def(s)


    def test_handle_def(self):
        s = self.tok('\macro#1{#1}')
        m = {}
        handle_def(s,m)
        self.assertEqual(m['macro'], ([[],[]], list(self.tok('#1'))))


    def test_match_macro_pattern(self):
        (s,pattern) = read_params(self.tok('x{'))
        tokens = self.tok('x')
        (s, res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [])

        (s,pattern) = read_params(self.tok('x{'))
        tokens = self.tok('y')
        with self.assertRaises(TeXMatchError):
            res = match_macro_pattern(pattern,tokens)

        (s,pattern) = read_params(self.tok('#1{'))
        tokens = self.tok('x')
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('x'))])

        (s,pattern) = read_params(self.tok('#1{'))
        tokens = self.tok('{x}')
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('x'))])

        (s,pattern) = read_params(self.tok('#1 delimiter {'))
        tokens = self.tok(' match result delimiter ')
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok(' match result'))])

        (s,pattern) = read_params(self.tok('#1 delimiter {'))
        tokens = self.tok(' match {result delimiter ')
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok(' match {result'))])

        (s,pattern) = read_params(self.tok('#1#2{'))
        tokens = self.tok('xy')
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('x')), list(self.tok('y'))])

        (s,pattern) = read_params(self.tok('p#1d{'))
        tokens = self.tok('p{he{ll}o}dxd2 some text \par')
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('{he{ll}o}'))])

        (s,pattern) = read_params(self.tok('p#1d#2d2{'))
        tokens = self.tok('p{he{ll}o}dxd2 some text \par')
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res),
                [list(self.tok('{he{ll}o}')),
                 list(self.tok('x')) ])

        (s,pattern) = read_params(self.tok('p#1d#2d2#3\par{'))
        tokens = self.tok('p{he{ll}o}dxd2 some text \par')
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(
                list(res),
                [list(self.tok('{he{ll}o}')),
                 list(self.tok('x')),
                 list(self.tok_exact(' some text '))])

        (s,pattern) = read_params(self.tok('#1{'))
        tokens = self.tok('')
        with self.assertRaises(TeXMatchError):
            list(match_macro_pattern(pattern,tokens))

        (s,pattern) = read_params(self.tok('#1#2#3{'))
        tokens = self.tok_exact('ab')
        with self.assertRaises(TeXMatchError):
            list(match_macro_pattern(pattern,tokens))


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
        s = self.tok('\def\macro#1{#1 #1}')
        b = expand(s)
        self.assertEqual(list(b), list(self.tok('')))

        s = self.tok('\def\macro#1{#1 #1}\macro{Hello}')
        b = expand(s)
        self.assertEqual(list(b), list(self.tok('Hello Hello')))

        s = self.tok('\def\macro#1{#1 #1}\\unknownmacro{Hello}')
        b = expand(s)
        self.assertEqual(list(b), list(self.tok('\\unknownmacro{Hello}')))

        s = self.tok('\def\macro#1{#1 #1}\\unknownmacro{\macro{Hello}}')
        b = expand(s)
        self.assertEqual(list(b), list(self.tok('\\unknownmacro{Hello Hello}')))

        s = self.tok('\macro{\def\mac{one}\mac}')
        b = expand(s, usermacros={})
        self.assertEqual(list(b), list(self.tok('\macro{one}')))

        s = self.tok('\def\m#1#2{}\m')
        with self.assertRaises(TeXMatchError):
            list(expand(s, usermacros={}))

        s = self.tok('\def\m#1#2{#1#2}\m\m\m   ')
        with self.assertRaises(TeXMatchError):
            list(expand(s, usermacros={}))

        s = self.tok('\def\m#1#2{#1#2}\m{\m{}{}}\m{}{}')
        b = expand(s, usermacros={})
        self.assertEqual(list(b), list(self.tok('')))

if __name__ == '__main__':
    unittest.main()

