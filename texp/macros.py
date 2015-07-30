
from texp.stream import *
from texp.tokenizer import *


def has_catcode(t, catcode):
    return is_tokencode(t) and t.catcode == catcode

def read_params(tokenstream):
    arg_nr = 1
    curr_arg = []
    args = []
    while True:
        prev_tokenstream = tokenstream
        (t, tokenstream) = tokenstream.next()
        if has_catcode(t, CatCode.param):
            (n, tokenstream) = tokenstream.next()
            if is_tokencode(n):
                try:
                    i = int(n.tok)
                except ValueError:
                    raise MatchError("Invalid argument char '%s'" % n.tok, n.pos)
                if i == 0:
                    raise MatchError("Parameter cannot be 0", n.pos)
                if i != arg_nr:
                    raise MatchError("Arguments need to be sequential", n.pos)
                args.append(curr_arg)
                arg_nr = arg_nr + 1
                curr_arg = []
            else:
                raise MatchError("Not an integer", n.pos)
        elif has_catcode(t, CatCode.begin_group):
            tokenstream = prev_tokenstream
            args.append(curr_arg)
            break
        else:
            curr_arg.append(t)
    return (tokenstream, args)


def read_body(tokenstream):
    n = 1
    (t, tokenstream) = tokenstream.next()
    start_pos = t.pos
    body = []
    if has_catcode(t, CatCode.begin_group):
        while True:
            (t, tokenstream) = tokenstream.next()
            if has_catcode(t, CatCode.begin_group):
                n = n + 1
            elif has_catcode(t, CatCode.end_group):
                n = n - 1
            if n == 0:
                break
            body.append(t)
    else:
        raise MatchError("Failed to parse body", start_pos)
    return (tokenstream, body)


def find_params(tokens):
    for i in tokens:
        if has_catcode(i, CatCode.param):
            yield next(tokens)

def find_highest_param(tokens):
    params = [int(x.tok) for x in find_params(tokens)]
    if len(params) == 0:
        return None
    return max (params)


def read_def(tokenstream):
    (cname, tokenstream) = tokenstream.next()

    if not(is_controlsequence(cname)):
        raise MatchError("Control sequence expected", cname.pos)

    (tokenstream, params) = read_params(tokenstream)
    (tokenstream, body) = read_body(tokenstream)
    h = find_highest_param(iter(body))
    if h == 0:
        raise MatchError("0 cannot be a parameter", cname.pos)
    if h is None:
        h = 0
    if h > len(list(params)) - 1:
        raise MatchError("Body has undefined parameters", cname.pos)
    return (tokenstream, cname, params, body)


def params_body_to_macro(params,body):
    def macro(tokenstream, state):
        (tokenstream, matches) = match_macro_pattern(params,tokenstream)
        expansion = expand_params(body, matches)
        return concat_func_streams(func_stream(expansion), tokenstream)
    macro.definition = (params, body)
    return macro


def macro_def (tokenstream, state):
    (tokenstream,cname,params,body) = read_def(tokenstream)
    state.macros[cname.name] = params_body_to_macro(params, body)
    return tokenstream


# assumes that the begin_group token was consumed before calling this
def next_group(tokenstream):
    n = 1
    x = []

    t, _ = tokenstream.next()
    if t is None:
        raise MatchError("End of stream unexpected while reading a group")

    pos = t.pos

    while True:
        t, tokenstream = tokenstream.next()

        if t is None:
            raise MatchError("End of stream unexpected while reading a group", pos)

        if has_catcode(t, CatCode.begin_group):
            n += 1
        elif has_catcode(t, CatCode.end_group):
            n -= 1

        if n == 0:
            break

        x.append(t)

    return (tokenstream, x)


def next_token_or_group(tokenstream):
    (t, tokenstream) = tokenstream.next()
    if t is None:
        return (tokenstream, None)
    if has_catcode(t, CatCode.begin_group):
        return next_group(tokenstream)
    else:
        return (tokenstream, [t])


def match_prefix(pref, tokenstream):
    ts = tokenstream
    for i in pref:
        (x, tokenstream) = tokenstream.next()
        if x is None:
            return (ts, False)
        if i != x:
            return (ts, False)
    return (tokenstream, True)


def match_macro_pattern(pattern, tokenstream):
    tokens = pattern[0]

    # match the first pattern
    for t in tokens:
        tok, tokenstream = tokenstream.next()
        if t != tok:
            raise MatchError("Pattern does not match", tok.pos)

    matches = []
    m = []
    ts = tokenstream

    t, _ = tokenstream.next()
    pos = t.pos if t is not None else None

    for tokens in pattern[1:]:
        if len(tokens) == 0: # non-delimited token
            (ts, m) = next_token_or_group(ts)
            if m is None:
                raise MatchError("Stream ended while matching a macro pattern", pos)
            matches.append(m)
        else: # delimited, append until match is found
            while True:
                (ts, matched) = match_prefix(tokens, ts)
                if matched:
                    matches.append(m)
                    m = []
                    break
                else:
                    (x, ts) = ts.next()
                    if x is None:
                        raise MatchError("Stream ended while matching a macro pattern", pos)
                    m.append(x)
    return (ts, matches)


# body and args should be lists of tokens
def expand_params(body, args):
    expanded = []
    b = iter(body)
    for i in b:
        if has_catcode(i, CatCode.param):
            n = next(b, None)
            if n is None:
                raise Exception("Malformed body, the body ended with a param token without the correspoding number")
            for x in args[int(n.tok) - 1]:
                expanded.append(x)
        else:
            expanded.append(i)
    return expanded


def define_macro(args, f):
    def macro (tokenstream, state):
        a = []
        for i in args:
            (tokenstream, x) = next_token_or_group(tokenstream)
            if x is None:
                raise MatchError("End of stream while matching arguments")
            if i == 'e':
                a.append(list(expand(iter(x), state)))
            else:
                a.append(x)

        res = f(state, *a)
        return concat_func_streams(func_stream(res), tokenstream)

    return macro


# a decorator that uses the macro patterns of the def command to define a builtin macro
# @define_macro_pat('#1=#2')
# def swap(state, x, y):
#     return list(y) + list(x)
# s.macros['m'] = swap
def define_macro_pat(pattern):
    _, params = read_params(func_stream(tokenize(iter_pos(pattern + '{'))))
    def wrap(f):
        def macro(tokenstream, state):
            tokenstream, matches = match_macro_pattern(params, tokenstream)
            res = f(state, *matches)
            return concat_func_streams(func_stream(res), tokenstream)
        return macro
    return wrap



@define_macro_pat('#1=#2')
def macro_catcode(state, t, n):
    # expand the args
    t = list(expand(iter(t), state))
    n = list(expand(iter(n), state))

    if not (len(t) == 2 and all(is_tokencode(i) for i in t) and t[0].tok == '`'):
        raise MatchError("Unknown amount of arguments given to catcode")

    x = (i.tok for i in n)
    cc = int(''.join(x))

    if not (cc >= 0 and cc <= 15):
        raise MatchError("Unknown cat code given %d" % cc)

    state.catcode[t[1].tok] = cc

    return []


class expansion_state:
    def __init__(self, macros={}, catcode=catcode_map()):
        self.macros = macros.copy()
        self.catcode = catcode.copy()


def m_read_file(state, fname):
    n = tokenstream_to_str(fname)
    s = iter_pos(open(n).read())
    return expand(tokenize(s), state)


macro_read_file = define_macro(['e'], m_read_file)


class macro_dict(dict):

    def define(self, args, name=None):
        def func(f):
            n = f.__name__ if name is None else name
            self[n] = define_macro(args, f)
            return f
        return func


defaultbuiltinmacros = macro_dict({
    'def' : macro_def,
    'readfile' : macro_read_file,
    'catcode' : macro_catcode
})

#
# \macro.this
#
# \namespacestart{name}
# \namespaceend{name}
# \namespace{name}{ ... }
#


def expand(tokenstream, state=expansion_state(macros=defaultbuiltinmacros)):
    if not isinstance(tokenstream, func_stream):
        tokenstream = func_stream(tokenstream)

    while True:
        t, tokenstream = tokenstream.next()
        if t is None:
            break
        if is_controlsequence(t) and t.name in state.macros:
            m = state.macros[t.name]
            tokenstream = m(tokenstream, state)
        else:
            yield t

