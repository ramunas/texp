#!/usr/bin/env python3.4


class TeXException(Exception):
    pass

class TeXMatchError(Exception):
    pass


class func_stream:
    __slots__ = 'it', 'next_stream', 'buf'

    def __init__(self, iterable):
        self.it = iter(iterable)
        self.next_stream = None
        self.buf = None

    def next(self):
        if self.next_stream is None:
            self.next_stream = func_stream(self.it)
            self.buf = next(self.it, None)
        return (self.buf, self.next_stream)

    def prepend(self, x):
        s = func_stream(self.it)
        s.next_stream = self
        s.buf = x
        return s


class concat_func_streams(func_stream):
    __slots__ = 'f1', 'f2'

    def __init__(self, f1, f2):
        self.f1 = f1
        self.f2 = f2

    def next(self):
        (v, s) = self.f1.next()
        if v is None:
            return self.f2.next()
        return (v, concat_func_streams(s, self.f2))

    def prepend(self,x):
        self.f1 = self.f1.prepend(x)
        return self


class CatCode:
    escape      = 0   # Escape character, normally '\'
    begin_group = 1   # Begin grouping, normally {
    end_group   = 2   # End grouping, normally }
    math_shift  = 3   # Math shift, normally $
    align_tab   = 4   # Alignment tab, normally &
    end_of_line = 5   # End of line, normally <return>
    param       = 6   # Parameter, normally #
    superscript = 7   # Superscript, normally ^
    subscript   = 8   # Subscript, normally _
    ignored     = 9   # Ignored character, normally <null>
    space       = 10  # Space, normally <space> and <tab>
    letter      = 11  # Letter, normally only contains the letters a,...,z and A,...,Z. These characters can be used in command names
    other       = 12  # Other, normally everything else not listed in the other categories
    active      = 13  # Active character, for example ~
    comment     = 14  # Comment character, normally %
    invalid     = 15  # Invalid character, normally <delete>


class CharCatCodeTable(dict):
    def __init__(self):
        self.update({
            '\\' : CatCode.escape,
            '{'  : CatCode.begin_group,
            '}'  : CatCode.end_group,
            '$'  : CatCode.math_shift,
            '&'  : CatCode.align_tab,
            '\n' : CatCode.end_of_line,
            '#'  : CatCode.param,
            '^'  : CatCode.superscript,
            '_'  : CatCode.subscript,
            '~'  : CatCode.active,
            '%'  : CatCode.comment
            })

    def __missing__(self, key):
        if key.isspace():
            return CatCode.space
        elif key.isalpha():
            return CatCode.letter
        else:
            return CatCode.other


defaultcatcode_table = CharCatCodeTable()


class control_sequence:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '\\' + self.name

    def __eq__(self,x):
        return isinstance(x, control_sequence) and x.name == self.name


class token_code:
    def __init__(self, t, catcode):
        self.tok = t
        self.catcode = catcode

    def __repr__(self):
        return ('"%s" %s' % (self.tok, self.catcode))

    def __eq__(self,x):
        return isinstance(x, token_code) and x.catcode == self.catcode and x.tok == self.tok


def is_controlsequence(t):
    return isinstance(t, control_sequence)

def is_tokencode(t):
    return isinstance(t, token_code)

def tokenstream_to_str(tokenstream):
    r = ''
    for x in tokenstream:
        if is_tokencode(x):
            r = r + x.tok
        else:
            raise TeXException('Cannot convert the control sequence "%s" to a string' % x.name)
    return r



def read_control_sequence(bstream, state, catcode_table):
    name = ''

    (n, bstream) = bstream.next()
    if n is None:
        raise TeXException("End of file unexpected while parsing a control sequence")

    if catcode_table[n] != CatCode.escape:
        raise TeXException("Escape char expected")

    (n, bstream) = bstream.next()
    if n is None:
        raise TeXException("End of file unexpected while parsing a control sequence")

    cc = catcode_table[n]
    if cc == CatCode.letter:
        name = n
        while True:
            (char, bstream) = bstream.next()
            if char is None:
                break
            if catcode_table[char] != CatCode.letter:
                bstream = bstream.prepend(char)
                break
            name = name + char
        state = StreamState.skipping_blanks
    elif cc == CatCode.end_of_line:
        state = StreamState.middle
    else:
        name = n
        state = StreamState.skipping_blanks

    return (bstream, state, name)


def drop_line(bstream, state, catcode_table):
    while True:
        (c, bstream) = bstream.next()
        if c is None:
            break
        if catcode_table[c] == CatCode.end_of_line:
            break

    state = StreamState.new_line
    return (bstream, state)


# TeXbook, p. 46
class StreamState:
    middle          = 0
    new_line        = 1
    skipping_blanks = 2


def nexttoken(bstream, state, catcode_table):
    (c, bstream) = bstream.next()
    if c != None:
        cc = catcode_table[c]

        if cc == CatCode.escape:
            (bstream,state,cs) = read_control_sequence(bstream.prepend(c), state, catcode_table)
            return (bstream, state, control_sequence(cs))
        elif cc == CatCode.space:
            if state == StreamState.new_line:
                return nexttoken(bstream, state, catcode_table)
            elif state == StreamState.skipping_blanks:
                return nexttoken(bstream, state, catcode_table)
            else:
                state = StreamState.skipping_blanks
                return (bstream, state, token_code(' ', CatCode.space))
        elif cc == CatCode.ignored:
            return nexttoken(bstream, state, catcode_table)
        elif cc == CatCode.end_of_line:
            if state == StreamState.new_line:
                state = StreamState.skipping_blanks
                return (bstream, state, control_sequence('par'))
            elif state == StreamState.middle:
                state = StreamState.new_line
                return (bstream, state, token_code(' ', CatCode.space))
            elif state == StreamState.skipping_blanks:
                return nexttoken(bstream, state, catcode_table)
        elif cc == CatCode.comment:
            (bstream, state) = drop_line(bstream, state, catcode_table)
            return nexttoken(bstream, state, catcode_table)
        else:
            state = StreamState.middle
            return (bstream, state, token_code(c, cc))

    return (bstream, state, None)



def tokenstream(bstream, state=StreamState.new_line, catcode_table=defaultcatcode_table):
    if not isinstance(bstream, func_stream):
        bstream = func_stream(bstream)

    while True:
        (bstream, state, t) = nexttoken(bstream, state, catcode_table)
        if t is None:
            break
        yield t



def has_catcode(t, catcode):
    return is_tokencode(t) and t.catcode == catcode


def read_params(tokenstream):
    arg_nr = 1
    curr_arg = []
    args = []
    while True:
        (t, tokenstream) = tokenstream.next()
        if has_catcode(t, CatCode.param):
            (n, tokenstream) = tokenstream.next()
            if is_tokencode(n):
                try:
                    i = int(n.tok)
                except ValueError:
                    raise TeXMatchError("Invalid argument char '%s'" % n.tok)
                if i == 0:
                    raise TeXMatchError("Parameter cannot be 0")
                if i != arg_nr:
                    raise TeXMatchError("Arguments need to be sequential")
                args.append(curr_arg)
                arg_nr = arg_nr + 1
                curr_arg = []
            else:
                raise TeXMatchError("Not an integer")
        elif has_catcode(t, CatCode.begin_group):
            tokenstream = tokenstream.prepend(t)
            args.append(curr_arg)
            break
        else:
            curr_arg.append(t)
    return (tokenstream, args)


def read_body(tokenstream):
    n = 1
    (t, tokenstream) = tokenstream.next()
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
        raise TeXException("Failed to parse body")
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
        raise TeXMatchError("Control sequence expected")

    (tokenstream, params) = read_params(tokenstream)
    (tokenstream, body) = read_body(tokenstream)
    h = find_highest_param(iter(body))
    if h == 0:
        raise TeXException("0 cannot be a parameter")
    if h is None:
        h = 0
    if h > len(list(params)) - 1:
        raise TeXException("Body has undefined parameters")
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
    while True:
        (t, tokenstream) = tokenstream.next()

        if t is None:
            raise TeXMatchError("End of stream unexpected while reading a group")

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
        (tok, tokenstream) = tokenstream.next()
        if t != tok:
            raise TeXMatchError("Pattern does not match")

    matches = []
    m = []
    ts = tokenstream
    for tokens in pattern[1:]:
        if len(tokens) == 0: # non-delimited token
            (ts, m) = next_token_or_group(ts)
            if m is None:
                raise TeXMatchError("Stream ended while matching a macro pattern")
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
                        raise TeXMatchError("Stream ended while matching a macro pattern")
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
                raise TeXException("Malformed body, the body ended with a pram token without the correspoding number")
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
                raise TeXMatchError("End of stream while matching arguments")
            if i == 'e':
                a.append(list(expand(iter(x), state)))
            else:
                a.append(x)

        res = f(state, *a)
        return concat_func_streams(func_stream(res), tokenstream)

    return macro



class expansion_state:
    def __init__(self, macros={}):
        self.macros = macros.copy()


def m_read_file(state, fname):
    n = tokenstream_to_str(fname)
    s = iter(open(n).read())
    return expand(tokenstream(s), state)


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
    'readfile' : macro_read_file
})

def expand(tokenstream, state=expansion_state(macros=defaultbuiltinmacros)):
    if not isinstance(tokenstream, func_stream):
        tokenstream = func_stream(tokenstream)

    while True:
        (t, tokenstream) = tokenstream.next()
        if t is None:
            break
        if is_controlsequence(t) and t.name in state.macros:
            m = state.macros[t.name]
            tokenstream = m(tokenstream, state)
        else:
            yield t


