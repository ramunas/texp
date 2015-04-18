from texp.stream import *


class MatchError(Exception):
    def __init__(self, msg, pos=None):
        super().__init__(msg, pos)


class position:
    __slots__ = 'filename', 'col', 'ln'

    def __init__(self, filename=None, col=1, ln=1):
        self.filename = filename
        self.col = col
        self.ln = ln

    def __str__(self):
        return '%s:%d:%d' % \
                (self.filename if self.filename is not None else '-', self.ln, self.col)

    __repr__ = __str__


def iter_pos(it, filename=None, col=1, ln=1):
    it = iter(it)
    for x in it:
        if x == '\n':
            col = 1
            ln += 1
        else:
            col += 1

        yield x, position(filename, col, ln)



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


class catcode_map(dict):
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

    def copy(self):
        n = type(self)()
        n.update(self)
        return n


defaultcatcode_table = catcode_map()


class control_sequence:
    __slots__ = 'name', 'pos'

    def __init__(self, name, pos=None):
        self.name = name
        self.pos = pos

    def __repr__(self):
        return '\\' + self.name

    def __eq__(self,x):
        return isinstance(x, control_sequence) and x.name == self.name


class token_code:
    __slots__ = 'tok', 'catcode', 'pos'

    def __init__(self, t, catcode, pos=None):
        self.tok = t
        self.catcode = catcode
        self.pos = pos

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
            raise Exception('Cannot convert the control sequence "%s" to a string' % x.name)
    return r



def read_control_sequence(bstream, state, catcode_table):
    name = ''

    n, bstream = bstream.next()
    if n is None:
        raise MatchError("End of file unexpected while parsing a control sequence")

    n, pos = n

    if catcode_table[n] != CatCode.escape:
        raise MatchError("Escape char expected", pos)

    n, bstream = bstream.next()
    if n is None:
        raise MatchError("End of file unexpected while parsing a control sequence", pos)

    n, pos = n

    cc = catcode_table[n]
    if cc == CatCode.letter:
        name = n
        while True:
            prev_bstream = bstream
            char, bstream = bstream.next()
            if char is None:
                break
            char,pos = char

            if catcode_table[char] != CatCode.letter:
                bstream = prev_bstream
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
        c, bstream = bstream.next()
        if c is None:
            break
        c,pos = c
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
    prev_bstream = bstream
    c, bstream = bstream.next()
    if c != None:
        c, pos = c
        cc = catcode_table[c]

        if cc == CatCode.escape:
            (bstream,state,cs) = read_control_sequence(prev_bstream, state, catcode_table)
            return (bstream, state, control_sequence(cs, pos))
        elif cc == CatCode.space:
            if state == StreamState.new_line:
                return nexttoken(bstream, state, catcode_table)
            elif state == StreamState.skipping_blanks:
                return nexttoken(bstream, state, catcode_table)
            else:
                state = StreamState.skipping_blanks
                return (bstream, state, token_code(' ', CatCode.space, pos=pos))
        elif cc == CatCode.ignored:
            return nexttoken(bstream, state, catcode_table)
        elif cc == CatCode.end_of_line:
            if state == StreamState.new_line:
                state = StreamState.skipping_blanks
                return (bstream, state, control_sequence('par'))
            elif state == StreamState.middle:
                state = StreamState.new_line
                return (bstream, state, token_code(' ', CatCode.space, pos=pos))
            elif state == StreamState.skipping_blanks:
                return nexttoken(bstream, state, catcode_table)
        elif cc == CatCode.comment:
            (bstream, state) = drop_line(bstream, state, catcode_table)
            return nexttoken(bstream, state, catcode_table)
        else:
            state = StreamState.middle
            return (bstream, state, token_code(c, cc, pos=pos))

    return (bstream, state, None)



def tokenize(bstream, state=StreamState.new_line, catcode_table=defaultcatcode_table):
    if not isinstance(bstream, func_stream):
        bstream = func_stream(bstream)

    while True:
        (bstream, state, t) = nexttoken(bstream, state, catcode_table)
        if t is None:
            break
        yield t


