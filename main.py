#!/usr/bin/env python3.4

from enum import Enum
import itertools


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


class Token(object):
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

def is_controlsequence(t):
    return t.__class__ == ControlSequence

def is_tokencode(t):
    return t.__class__ == TokenCode


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

def has_catcode(x, catcode):
    return x.__class__ == TokenCode and x.catcode == catcode

def handle_def (tokenstream):
    args = []
    curr_arg = []
    body = []
    arg_nr = 1
    name = next(tokenstream)
    if not(is_controlsequence(name)):
        raise TeXException ("Invalid name for a macro %s" % name)
    print (name)
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
                n = 1
                while True:
                    c = next(tokenstream)
                    if c == None:
                        raise TeXException("End of file unexpected while handling def")
                    if is_tokencode(c):
                        if c.catcode == CatCode.begin_group:
                            n = n + 1
                        elif c.catcode == CatCode.end_group:
                            n = n - 1
                        # elif c.catcode == CatCode.param:
                        #     p = tokenstream.__next__()
                    if n == 0:
                        break
                    body.append(c)
                break
            else:
                curr_arg.append(c)
        elif c == None:
            raise TeXException("End of file unexpected while handling def")

    userdefinedmacros[name.name] = (args,body)


builtinmacros = {
        'def' : handle_def
        }

def expand(tokenstream):
    tstream = tokenstream
    for t in tstream:
        if is_controlsequence(t):
            m = builtinmacros.get(t.name)
            um = userdefinedmacros.get(t.name)
            if m != None:
                m(tstream)
                # print ("yes")

# print (list(tokenstream(peakable(bytestream('main.tex')))))
expand(tokenstream(peakable(bytestream('test2.tex'))))
print (userdefinedmacros);
# expand(tokenstream(peakable(bytestream('main.tex'))))

