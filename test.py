#!/usr/bin/env python3
import unittest
import weakref
import gc
from texp import *


class TestOther(unittest.TestCase):
    def test_func_stream(self):
        it = iter([1,2,3])

        s1 = func_stream(it)
        (v,s2) = s1.next()
        self.assertEqual(v, 1)
        (v,s3) = s2.next()
        self.assertEqual(v, 2)

        # it is functional, calling again will return the same stream
        (v,s2) = s1.next()
        self.assertEqual(v, 1)
        (v,s3) = s2.next()
        self.assertEqual(v, 2)

        x = next(it)
        self.assertEqual(x, 3)



class TestTeX(unittest.TestCase):

    def setUp(self):
        # called each time a test is run
        pass

    def tok(self,s):
        return tokenize(iter_pos(iter(s)))

    def ftok(self, s):
        return func_stream(self.tok(s))

    def tok_exact(self,s):
        return tokenize(iter_pos(s), state=StreamState.middle)

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
        rs = func_stream([1,2,3,4])
        (s, res) = match_prefix(iter([1,2,3]), rs)
        self.assertTrue(res)
        (v, _) = s.next()
        self.assertEqual(4, v)

        rs = func_stream([1,2,3,4])
        (s, res) = match_prefix(iter([1,2,4]), rs)
        self.assertFalse(res)
        (v, _) = s.next()
        self.assertEqual(1, v)

        rs = func_stream([1,2,3,4])
        (s, res) = match_prefix(iter([6,2,4]), rs)
        self.assertFalse(res)
        (v, _) = s.next()
        self.assertEqual(1, v)


    def test_read_control_sequence(self):
        state = StreamState.middle
        t = defaultcatcode_table
        s = func_stream(iter_pos('\macro'))
        (s,st,r) = read_control_sequence(s, state, t)
        self.assertEqual('macro',r)

        with self.assertRaises(TeXMatchError):
            read_control_sequence(func_stream(iter_pos('macro')), state, t)

        with self.assertRaises(TeXMatchError):
            read_control_sequence(func_stream(iter_pos('\\')), state, t)

        r = read_control_sequence(func_stream(iter_pos('\=')), state, t)
        self.assertEqual('=',r[2])

        r = read_control_sequence(func_stream(iter_pos('\~')), st, t)
        self.assertEqual('~',r[2])

        r = read_control_sequence(func_stream(iter_pos("\\\n")), st, t)
        self.assertEqual('',r[2])

    def test_tokenize(self):
        text = 'text'
        s = iter(text)
        e = [ token_code(x, CatCode.letter) for x in iter(text) ]
        t = list(tokenize(iter_pos(s)))
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
        s = iter_pos(text)
        t = list(tokenize(s))
        e = [control_sequence('macro'), token_code('x', CatCode.letter)]
        self.assertEqual(t, e)

    def test_next_group(self):
        s = self.ftok('group}')
        (s,group) = next_group(s)
        res = list(tokenize(iter_pos('group')))
        self.assertEqual(res, list(group))

        s = self.ftok('{group}')
        with self.assertRaises(TeXMatchError):
            group = next_group(s)

    def test_next_token_or_group(self):
        s = self.ftok('')
        (s, r) = next_token_or_group(s)
        self.assertEqual(r, None)

        s = self.ftok('{group}')
        (s,group) = next_token_or_group(s)
        res = list(tokenize(iter_pos('group')))
        self.assertEqual(res, list(group))

        s = self.ftok('g')
        (s,group) = next_token_or_group(s)
        res = list(tokenize(iter_pos('g')))
        self.assertEqual(res, list(group))


    def test_read_params(self):
        s = func_stream(self.tok('{'))
        args = read_params(s)
        self.assertEqual([[]], args[1])

        s = func_stream(self.tok('#1{'))
        args = read_params(s)
        self.assertEqual([[],[]], args[1])

        s = func_stream(self.tok('#1delim{'))
        args = read_params(s)
        self.assertEqual([[],list(self.tok('delim'))], args[1])

        s = func_stream(self.tok('#1#2{'))
        args = read_params(s)
        self.assertEqual([[],[],[]], args[1])

        s = func_stream(self.tok('#1#3{'))
        with self.assertRaises(TeXMatchError):
            args = read_params(s)

        s = func_stream(self.tok('#a{'))
        with self.assertRaises(TeXMatchError):
            args = read_params(s)

        s = func_stream(self.tok('#0{'))
        with self.assertRaises(TeXMatchError):
            args = read_params(s)

        s = func_stream(self.tok('pref#1delim1#2delim2{'))
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
        s1 = self.ftok("{%s}" % t)
        s2 = self.tok(t)
        (s,b) = read_body(s1)
        self.assertEqual(list(b), list(s2))

    def test_read_def(self):
        s = func_stream(self.tok("\\name{}"))
        (s,n,p,b) = read_def(s)
        self.assertEqual(n.name, "name")
        self.assertEqual([[]], p)
        self.assertEqual(list(b), list(self.tok('')))

        s = self.ftok("\\name#1#2#3{#1#2#3}")
        (s, n,p,b) = read_def(s)
        self.assertEqual(n.name, "name")
        self.assertEqual([[],[],[],[]], p)
        self.assertEqual(list(b), list(self.tok("#1#2#3")))

        s = self.ftok("\\macro{#0}")
        with self.assertRaises(TeXMatchError):
            (s, n,p,b) = read_def(s)

        s = self.ftok("\\macro{#1}")
        with self.assertRaises(TeXMatchError):
            (s, n,p,b) = read_def(s)

        s = self.ftok("\\name#1#2#3{#1#2#4#3}")
        with self.assertRaises(TeXMatchError):
            (s, n,p,b) = read_def(s)


    def test_macro_def(self):
        s = self.ftok('\macro#1{#1}')
        m = expansion_state()
        macro_def(s,m)
        self.assertEqual(m.macros['macro'].definition, ([[],[]], list(self.tok('#1'))))


    def test_match_macro_pattern(self):
        (s,pattern) = read_params(func_stream(self.tok('x{')))
        tokens = func_stream(self.tok('x'))
        (s, res) = match_macro_pattern(pattern, tokens)
        self.assertEqual(list(res), [])

        (s,pattern) = read_params(func_stream(self.tok('x{')))
        tokens = func_stream(self.tok('y'))
        with self.assertRaises(TeXMatchError):
            res = match_macro_pattern(pattern, tokens)

        (s,pattern) = read_params(func_stream(self.tok('#1{')))
        tokens = func_stream(self.tok('x'))
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('x'))])

        (s,pattern) = read_params(func_stream(self.tok('#1{')))
        tokens = func_stream(self.tok('{x}'))
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('x'))])

        (s,pattern) = read_params(func_stream(self.tok('#1 delimiter {')))
        tokens = func_stream(self.tok(' match result delimiter '))
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok(' match result'))])

        (s,pattern) = read_params(func_stream(self.tok('#1 delimiter {')))
        tokens = func_stream(self.tok(' match {result delimiter '))
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok(' match {result'))])

        (s,pattern) = read_params(func_stream(self.tok('#1#2{')))
        tokens = func_stream(self.tok('xy'))
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('x')), list(self.tok('y'))])

        (s,pattern) = read_params(func_stream(self.tok('p#1d{')))
        tokens = func_stream(self.tok('p{he{ll}o}dxd2 some text \par'))
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res), [list(self.tok('{he{ll}o}'))])

        (s,pattern) = read_params(func_stream(self.tok('p#1d#2d2{')))
        tokens = func_stream(self.tok('p{he{ll}o}dxd2 some text \par'))
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(list(res),
                [list(self.tok('{he{ll}o}')),
                 list(self.tok('x')) ])

        (s,pattern) = read_params(func_stream(self.tok('p#1d#2d2#3\par{')))
        tokens = func_stream(self.tok('p{he{ll}o}dxd2 some text \par'))
        (s,res) = match_macro_pattern(pattern,tokens)
        self.assertEqual(
                list(res),
                [list(self.tok('{he{ll}o}')),
                 list(self.tok('x')),
                 list(self.tok_exact(' some text '))])

        (s,pattern) = read_params(func_stream(self.tok('#1{')))
        tokens = func_stream(self.tok(''))
        with self.assertRaises(TeXMatchError):
            list(match_macro_pattern(pattern,tokens))

        (s,pattern) = read_params(func_stream(self.tok('#1#2#3{')))
        tokens = func_stream(self.tok_exact('ab'))
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
        new_state = expansion_state(macros=defaultbuiltinmacros)
        b = expand(s, state=new_state)
        self.assertEqual(list(b), list(self.tok('\macro{one}')))

        s = self.tok('\def\m#1#2{}\m')
        with self.assertRaises(TeXMatchError):
            new_state = expansion_state(macros=defaultbuiltinmacros)
            list(expand(s, state=new_state))

        s = self.tok('\def\m#1#2{#1#2}\m\m\m   ')
        with self.assertRaises(TeXMatchError):
            new_state = expansion_state(macros=defaultbuiltinmacros)
            list(expand(s, state=new_state))

        s = self.tok('\def\m#1#2{#1#2}\m{\m{}{}}\m{}{}')
        new_state = expansion_state(macros=defaultbuiltinmacros)
        b = expand(s, state=new_state)
        self.assertEqual(list(b), list(self.tok('')))


    def test_define_macro(self):
        s = expansion_state(macros=defaultbuiltinmacros)
        def swap(state, x, y):
            return list(y) + list(x)
        s.macros['m'] = define_macro(['','e'], swap)

        t = self.tok('\def\g#1{#1#1}\m{3}{\g{1}}')

        self.assertEqual(list(expand(t,s)), list(self.tok('113')))


    def test_macro_dict(self):
        macros = macro_dict()
        macros['def'] = macro_def

        @macros.define(['e'])
        def macro(state, arg):
            return arg + [token_code(x, CatCode.letter) for x in 'hello']

        @macros.define([], name='foo')
        def macro(state):
            return []

        self.assertTrue('macro' in macros)
        self.assertTrue('foo' in macros)

        t = self.tok('\def\m{World }\macro\m')
        s = expansion_state(macros=macros)

        self.assertEqual(list(expand(t,s)), list(self.tok('World hello')))


if __name__ == '__main__':
    unittest.main()

