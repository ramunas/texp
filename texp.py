#!/usr/bin/env python3.4

from enum import Enum
import itertools


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

class peakable(object):
    def __init__(self, stream):
        self.buf = None
        self.stream = stream

    def __peak__(self):
        if self.buf == None:
            self.buf = next(self.stream)
        return self.buf

    def __next__(self):
        x = self.__peak__()
        self.buf = None
        return x

    def __iter__(self):
        return self

class resetable(object):
    def __iter__(self): return self

    def __init__(self, stream):
        self.stream = stream
        self.read = []

    def __enter__(self):
        self.read.append([])
        return self

    def __reset__(self):
        s = self.read.pop()
        self.stream = itertools.chain(iter(s), self.stream)

    def __exit__(self, exc_type, exc_value, traceback):
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



# 0 = Escape character, normally \
# 1 = Begin grouping, normally {
# 2 = End grouping, normally }
# 3 = Math shift, normally $
# 4 = Alignment tab, normally &
# 5 = End of line, normally <return>
# 6 = Parameter, normally #
# 7 = Superscript, normally ^
# 8 = Subscript, normally _
# 9 = Ignored character, normally <null>
# 10 = Space, normally <space> and <tab>
# 11 = Letter, normally only contains the letters a,...,z and A,...,Z. These characters can be used in command names
# 12 = Other, normally everything else not listed in the other categories
# 13 = Active character, for example ~
# 14 = Comment character, normally %
# 15 = Invalid character, normally <delete>
class CatCode(Enum):
    escape      = 0
    begin_group = 1
    end_group   = 2
    math_shift  = 3
    align_tab   = 4
    end_of_line = 5
    param       = 6
    superscript = 7
    subscript   = 8
    ignored     = 9
    space       = 10
    letter      = 11
    other       = 12
    active      = 13
    comment     = 14
    invalid     = 15


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

defaulttable = CharCatCodeTable()


class Token(StructEq):
    pass


class ControlSequence(Token):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return '\\' + self.name


class TokenCode(Token):
    def __init__(self, t, catcode):
        self.tok = t
        self.catcode = catcode
    def __repr__(self):
        return ('"%s" %s' % (self.tok, self.catcode.name))


class ParamToken(Token):
    def __init__(self,n):
        self.number = n
    def __repr__(self):
        return "#%d" % self.number


def is_controlsequence(t):
    return t.__class__ == ControlSequence

def is_tokencode(t):
    return t.__class__ == TokenCode

def is_paramtoken(t):
    return t.__class__ == ParamToken


def control_sequence(bstream):
    name = ''
    next(bstream)
    cc = defaulttable[peak(bstream)]
    if cc == CatCode.letter:
        while defaulttable[peak(bstream)] == CatCode.letter:
            name = name + next(bstream)
        bstream.state = StreamState.skipping_blanks
    elif cc == CatCode.end_of_line:
        next(bstream)
        bstream.state = StreamState.middle
    else:
        name = next(bstream)
        bstream.state = StreamState.skipping_blanks

    return name

def drop_line(bstream):
    while True:
        c = next(bstream)
        if c == None:
            break
        if defaulttable[c] == CatCode.end_of_line:
            break

    bstream.state = StreamState.new_line


# TeXbook, p. 46
class StreamState(Enum):
    middle          = 0
    new_line        = 1
    skipping_blanks = 2

def nexttoken(bstream):
    c = peak(bstream, None)
    if c != None:
        cc = defaulttable[c]

        if cc == CatCode.escape:
            return ControlSequence(control_sequence(bstream))
        elif cc == CatCode.space:
            next(bstream)
            if bstream.state == StreamState.new_line:
                return nexttoken(bstream)
            elif bstream.state == StreamState.skipping_blanks:
                return nexttoken(bstream)
            else:
                bstream.state = StreamState.skipping_blanks
                return TokenCode(' ', CatCode.space)
        elif cc == CatCode.ignored:
            next(bstream)
            return nexttoken(bstream)
        elif cc == CatCode.end_of_line:
            next(bstream)
            if bstream.state == StreamState.new_line:
                bstream.state = StreamState.skipping_blanks
                return ControlSequence('par')
            elif bstream.state == StreamState.middle:
                bstream.state = StreamState.skipping_blanks
                return TokenCode(' ', CatCode.space)
            return nexttoken(bstream)
        elif cc == CatCode.comment:
            drop_line(bstream)
            return nexttoken(bstream)
        else:
            next(bstream)
            bstream.state = StreamState.middle
            return TokenCode(c, cc)

    return None


def tokenstream(bstream):
    bstream.state = StreamState.new_line
    while True:
        t = nexttoken(bstream)
        if t == None:
            break
        yield t


userdefinedmacros = {}


class TeXException(Exception):
    pass

def has_catcode(t, catcode):
    return is_tokencode(t) and t.catcode == catcode


def read_params(tokenstream):
    arg_nr = 1
    curr_arg = []
    args = []
    while True:
        t = peak(tokenstream)
        if has_catcode(t, CatCode.param):
            t = next(tokenstream)
            n = next(tokenstream)
            if is_tokencode(n):
                if int(n.tok) != arg_nr:
                    raise TeXException("Arguments need to be sequential")
                args.append(curr_arg)
                arg_nr = arg_nr + 1
                curr_arg = []
            else:
                raise TeXException("Not an integer")
        elif has_catcode(t, CatCode.begin_group):
            args.append(curr_arg)
            break
        else:
            curr_arg.append(next(tokenstream))
    return args


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
    return body



def handle_def (tokenstream):
    args = []
    curr_arg = []
    body = []
    arg_nr = 1
    name = next(tokenstream)
    if not(is_controlsequence(name)):
        raise TeXException ("Invalid name for a macro %s" % name)
    while True:
        c = next(tokenstream)
        if is_controlsequence(c):
            curr_arg.append(c)
        elif is_tokencode(c):
            if c.catcode == CatCode.param:
                n = next(tokenstream)
                if n.tok != str(arg_nr):
                    raise TeXException ("Arguments need to be sequential")
                args.append(curr_arg)
                arg_nr = arg_nr + 1
                curr_arg = []
            elif c.catcode == CatCode.begin_group:
                args.append(curr_arg)
                n = 1
                while True:
                    c = next(tokenstream, None)
                    if c == None:
                        raise TeXException("End of file unexpected while handling def")
                    if is_tokencode(c):
                        if c.catcode == CatCode.begin_group:
                            n = n + 1
                        elif c.catcode == CatCode.end_group:
                            n = n - 1
                        elif c.catcode == CatCode.param:
                            p = next(tokenstream)
                            c = ParamToken(int(p.tok))
                    if n == 0:
                        break
                    body.append(c)
                break
            else:
                curr_arg.append(c)
        elif c == None:
            raise TeXException("End of file unexpected while handling def")

    userdefinedmacros[name.name] = (args,body)


class TeXMatchError(Exception):
    pass


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
            matches.append(next_token_or_group(ts))
        else: # delimited, append until match is found
            try:
                while True:
                    if match_prefix(tokens, ts):
                        matches.append(m)
                        m = []
                        break
                    else:
                        m.append(next(ts))
            except StopIteration:
                raise TeXMatchError("Stream ended while matching a macro pattern")
    return matches


def expand_macro_body(body, args):
    for i in body:
        if is_paramtoken(i):
            for x in args[i.number - 1]:
                yield x
        else:
            yield i


def apply_macro(macro,stream):
    (pattern,body) = macro
    matches = match_macro_pattern(pattern,stream)
    return expand_macro_body(body, matches)


builtinmacros = {
        'def' : handle_def
        }

def expand(tokenstream):
    tstream = tokenstream
    while True:
        t = next(tstream, None)
        if t == None:
            break
        if is_controlsequence(t):
            if t.name in builtinmacros:
                m = builtinmacros[t.name]
                m(tstream)
            elif t.name in userdefinedmacros:
                m = userdefinedmacros[t.name]
                exp = apply_macro(m, tstream)
                tstream = itertools.chain(iter(exp),tstream)
            else:
                # pass through the unknown control sequences
                yield t
                # raise TeXMatchError("Undefined macro '%s'" % t.name)
        else:
            yield t


# expansion = expand(tokenstream(peakable(bytestream('test2.tex'))))

def main():
   expansion = expand(tokenstream(peakable(bytestream('test2.tex'))))

   print ("Expansion:")
   print (list(expansion))
   print ()
   print ("User defined macros:")
   print (userdefinedmacros)


if __name__ == '__main__':
    main ()

