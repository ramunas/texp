#!/usr/bin/env python3.4

import itertools


class TeXException(Exception):
    pass

class TeXMatchError(Exception):
    pass

class StructEq(object):
    def __eq__(self,x):
        return isinstance(self, x.__class__) and self.__dict__ == x.__dict__


def bytestream(file):
    f = open(file)
    while True:
        c = f.read(1)
        if not c:
            break
        yield c


def copytobuf(buf, it):
    while True:
        x = next(it)
        buf.append(x)
        yield x

def prepend(x, it):
    return itertools.chain(iter([x]), it)

class resetable(object):
    def __iter__(self): return self

    def __init__(self, stream):
        self.stream = stream
        self.read = []

    def __enter__(self):
        self.read.append([])
        return self

    def __drop__(self):
        return self.read.pop()

    def __reset__(self):
        s = self.__drop__()
        self.stream = itertools.chain(iter(s), self.stream)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type == None:
            self.__reset__()

    def __next__(self):
        x = next(self.stream)
        if len(self.read) != 0:
            self.read[-1].append(x)
        return x

    def __peak__(self):
        try:
            self.__enter__()
            x = next(self)
        finally:
            self.__reset__()
        return x


def peak(stream, *d):
    if len(d) == 0:
        return stream.__peak__()
    elif len(d) == 1:
        try:
            return stream.__peak__()
        except StopIteration:
            return d[0]
    else:
        raise TypeError ("peak expected at most 2 arguments, got %d" % len(d))


def is_peakable(t):
    return hasattr(t, '__peak__')

def is_resetable(t):
    return hasattr(t, '__reset__')

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


class ControlSequence:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return '\\' + self.name
    def __eq__(self,x):
        return x.__class__ == ControlSequence and x.name == self.name


class TokenCode:
    def __init__(self, t, catcode):
        self.tok = t
        self.catcode = catcode
    def __repr__(self):
        return ('"%s" %s' % (self.tok, self.catcode))
    def __eq__(self,x):
        return x.__class__ == TokenCode and x.catcode == self.catcode and x.tok == self.tok


def is_controlsequence(t):
    return t.__class__ == ControlSequence

def is_tokencode(t):
    return t.__class__ == TokenCode

def tokenstream_to_str(tokenstream):
    r = ''
    for x in tokenstream:
        if is_tokencode(x):
            r = r + x.tok
        else:
            raise TeXException('Cannot convert the control sequence "%s" to a string' % x.name)
    return r



def control_sequence(bstream, state, catcode_table):
    name = ''

    n = next(bstream,None)
    if n == None:
        raise TeXException("End of file unexpected while parsing a control sequence")

    if catcode_table[n] != CatCode.escape:
        raise TeXException("Escape char expected")

    n = next(bstream,None)
    if n == None:
        raise TeXException("End of file unexpected while parsing a control sequence")

    cc = catcode_table[n]
    if cc == CatCode.letter:
        name = n
        while True:
            char = next(bstream, None)
            if char == None:
                break
            if catcode_table[char] != CatCode.letter:
                bstream = prepend(char, bstream)
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
        c = next(bstream)
        if c == None:
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
    c = next(bstream, None)
    if c != None:
        cc = catcode_table[c]

        if cc == CatCode.escape:
            (bstream,state,cs) = control_sequence(prepend(c, bstream), state, catcode_table)
            return (bstream, state, ControlSequence(cs))
        elif cc == CatCode.space:
            if state == StreamState.new_line:
                return nexttoken(bstream, state, catcode_table)
            elif state == StreamState.skipping_blanks:
                return nexttoken(bstream, state, catcode_table)
            else:
                state = StreamState.skipping_blanks
                return (bstream, state, TokenCode(' ', CatCode.space))
        elif cc == CatCode.ignored:
            return nexttoken(bstream, state, catcode_table)
        elif cc == CatCode.end_of_line:
            if state == StreamState.new_line:
                state = StreamState.skipping_blanks
                return (bstream, state, ControlSequence('par'))
            elif state == StreamState.middle:
                state = StreamState.new_line
                return (bstream, state, TokenCode(' ', CatCode.space))
            elif state == StreamState.skipping_blanks:
                return nexttoken(bstream, state, catcode_table)
        elif cc == CatCode.comment:
            (bstream, state) = drop_line(bstream, state, catcode_table)
            return nexttoken(bstream, state, catcode_table)
        else:
            state = StreamState.middle
            return (bstream, state, TokenCode(c, cc))

    return (bstream, state, None)



def tokenstream(bstream, state=StreamState.new_line, catcode_table=defaultcatcode_table):
    while True:
        (bstream, state, t) = nexttoken(bstream, state, catcode_table)
        if t == None:
            break
        yield t



def has_catcode(t, catcode):
    return is_tokencode(t) and t.catcode == catcode


def read_params(tokenstream):
    arg_nr = 1
    curr_arg = []
    args = []
    while True:
        # t = peak(tokenstream)
        t = next(tokenstream)
        if has_catcode(t, CatCode.param):
            n = next(tokenstream)
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
            tokenstream = prepend(t, tokenstream)
            args.append(curr_arg)
            break
        else:
            curr_arg.append(t)
    return (tokenstream, args)


def read_body(tokenstream):
    n = 1
    t = next(tokenstream)
    body = []
    if has_catcode(t, CatCode.begin_group):
        while True:
            t = next(tokenstream)
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


def find_params(tokenstream):
    for i in tokenstream:
        if has_catcode(i, CatCode.param):
            yield next(tokenstream)

def find_highest_param(tokenstream):
    params = [int(x.tok) for x in find_params(tokenstream)]
    if len(params) == 0:
        return None
    return max (params)


def read_def(tokenstream):
    assert is_peakable(tokenstream)

    cname = next(tokenstream)
    if not(is_controlsequence(cname)):
        raise TeXException("Control sequence expected")
    params = read_params(tokenstream)
    body = read_body(tokenstream)
    h = find_highest_param(iter(body))
    if h == 0:
        raise TeXException("0 cannot be a parameter")
    if h == None:
        h = 0
    if h > len(list(params)) - 1:
        raise TeXException("Body has undefined parameters")
    return (cname, params, body)


def handle_def (tokenstream, userdefinedmacros):
    assert is_peakable(tokenstream)
    (cname,params,body) = read_def(tokenstream)
    userdefinedmacros[cname.name] = (params,body)




# assumes that the begin_group token was consumed before calling this
def next_group(tokenstream):
    n = 1
    x = []
    while True:
        t = next(tokenstream)
        if has_catcode(t, CatCode.begin_group):
            n = n + 1
        elif has_catcode(t, CatCode.end_group):
            n = n - 1

        if n == 0:
            break

        x.append(t)

    return x

def next_token_or_group(tokenstream):
    t = next(tokenstream)
    x = None
    if has_catcode(t, CatCode.begin_group):
        return next_group(tokenstream)
    else:
        return [t]


def match_prefix(pref, resetable_stream):
    with resetable_stream as s:
        for i in pref:
            x = next(s,None)
            if i != x:
                return False
    return True

def consume_prefix(pref, tokenstream):
    for i in pref:
        next(tokenstream)

def match_macro_pattern(pattern, tokenstream):
    tokens = pattern[0]

    # match the first pattern
    for t in tokens:
        if t != next(tokenstream):
            raise TeXMatchError("Pattern does not match")

    matches = []
    m = []
    ts = resetable(tokenstream)
    for tokens in pattern[1:]:
        if len(tokens) == 0: # non-delimited token
            try:
                matches.append(next_token_or_group(ts))
            except StopIteration:
                raise TeXMatchError("Stream ended while matching a macro pattern")
        else: # delimited, append until match is found
            try:
                while True:
                    if match_prefix(tokens, ts):
                        consume_prefix(tokens, ts)
                        matches.append(m)
                        m = []
                        break
                    else:
                        m.append(next(ts))
            except StopIteration:
                raise TeXMatchError("Stream ended while matching a macro pattern")
    return matches


# body and args should be lists of tokens
def expand_params(body, args):
    expanded = []
    b = iter(body)
    for i in b:
        if has_catcode(i, CatCode.param):
            n = next(b, None)
            if n == None:
                raise TeXException("Malformed body, the body ended with a pram token without the correspoding number")
            for x in args[int(n.tok) - 1]:
                expanded.append(x)
        else:
            expanded.append(i)
    return expanded


def apply_macro(macro,stream):
    (pattern,body) = macro
    matches = match_macro_pattern(pattern,stream)
    return expand_params(body, matches)



defaultbuiltinmacros = {
        'def' : handle_def
        }

def expand(tokenstream, builtinmacros=defaultbuiltinmacros, usermacros={}):
    assert is_resetable(tokenstream)
    assert is_peakable(tokenstream)

    while True:
        t = next(tokenstream, None)
        if t == None:
            break
        if is_controlsequence(t):
            if t.name in builtinmacros:
                m = builtinmacros[t.name]
                m(tokenstream, usermacros)
                # print ("Expanding builtin '%s'" % t.name)
            elif t.name in usermacros:
                m = usermacros[t.name]
                exp = apply_macro(m, tokenstream)
                tokenstream = resetable(itertools.chain(iter(exp), tokenstream))
                # print ("Expanding user '%s'" % t.name)
            else:
                yield t
        else:
            yield t


