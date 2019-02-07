#!/usr/bin/env python3

from collections import namedtuple

class MapStack():
    def __init__(self):
        self.map = [{}]
    def __getitem__(self, name):
        for x in reversed(self.map):
            if name in x:
                return x[name]
        raise KeyError()
    def __contains__(self, name):
        for x in reversed(self.map):
            if name in x:
                return True
        return False
    def __setitem__(self, name, value):
        self.map[-1][name] = value
    def pop(self):
        self.map.pop()
    def push(self):
        self.map.append({})

class InvalidCharacter(BaseException): pass

class TeXError(BaseException): pass


def exists(pred, iter):
    for x in iter:
        if pred(x):
            return True
    return False

def recursive_descent_matcher(rules, start, index, tokens):
    def iseof(tokens, idx):
        try: 
            x = tokens[idx]
            return False
        except IndexError: return True

    def parse(rule, idx):
        rs = [ (r,p,a) for r, p, a in rules if r == rule]
        for r,p,a in rs:
            i = idx
            match = []
            matched = True
            for x in p:
                if isinstance(x, str): # recursive or eof
                    if x == '⊣':
                        if not iseof(tokens, i):
                            matched = False
                            break
                    else:
                        res = parse(x, i)
                        if res is None: 
                            matched = False
                            break
                        (res, j) = res
                        match.append(res)
                        i = j
                else: # terminal
                    if iseof(tokens, i):
                        matched = False
                        break
                    if x(tokens[i]):
                        # print(tokens[i])
                        match.append(tokens[i])
                        i += 1
                    else:
                        matched = False
                        break
            if matched: return (a(match), i)
        return None
    return parse(start, index)



class TeX():

    __rules__ = {}
    __rules__['tokenizer'] = []
    __rules__['expander'] = []
    __rules__['command'] = []

    __commands__ = {}

    def step_rules(self, name):
        for i in self.__rules__[name]:
            if i(self):
                # print(i)
                return True
        return False

    def tokenize(self):
        return self.step_rules('tokenizer')
    
    def expand(self):
        return self.step_rules('expander')

    def execute(self):
        return self.step_rules('command')

    def step(self):
        return self.step_rules('command') or self.step_rules('expander') or self.step_rules('tokenizer')

    def accepting_state(self):
        return self.tokens == [] and self.input == '' and self.line == ''

    def run(self):
        while self.step():
            # self.print_state()
            pass
        if not self.accepting_state():
            print ("Got stuck while processing the following input on line", self.line_num)
            size = 75
            toks = ''.join([x for x, c in self.tokens[0:size]])
            l = self.line[0:size - len(toks)]
            i = self.input[0:size - len(toks) - len(l)]
            print('    "' + toks + l + i, '..."')
            # print(self.tokens[0:20])
            pass


    # Character category codes
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
    letter      = 11  # Letter, normally only contains the letters a,...,z and A,...,Z.
    other       = 12  # Other, normally everything else not listed in the other categories
    active      = 13  # Active character, for example ~
    comment     = 14  # Comment character, normally %
    invalid     = 15  # Invalid character, normally <delete>

    control_sequence = -1
    command = -2
    macro = -3
    parameter = -4

    class CatcodeMapStack(MapStack):
        def __getitem__(self, key):
            try:
                return super().__getitem__(key)
            except KeyError:
                cc = TeX.default_catcode(key)
                if cc < 0:
                    raise KeyError
                else:
                    return cc
        def __contains__(self, key):
            return (super().__contains__(key)) or (TeX.default_catcode(key) >= 0)

    class T():
        def __init__(self, size, get, populate):
            self.size = size
            self.get = get
            self.populate = populate

        def __getitem__(self, idx):
            top = None
            if isinstance(idx, slice):
                top = idx.stop
            else:
                top = idx
            if top < self.size(): return self.get(idx)
            while self.size() <= top:
                if not self.populate():
                    break
                    # raise IndexError
            return self.get(idx)

    Functional = namedtuple('Functional', ['params', 'body'])
    Builtin = namedtuple('Builtin', ['type'])


    @classmethod
    def default_catcode(self, char):
        if char.isalpha(): return self.letter
        if char.isnumeric(): return self.other
        if char == '\n': return self.end_of_line
        if char.isspace(): return self.space
        if char == '\\': return self.escape
        if char == '{': return self.begin_group
        if char == '}': return self.end_group
        if char == '$': return self.math_shift
        if char == '&': return self.align_tab
        if char == '\n': return self.end_of_line
        if char == '#': return self.param
        if char == '^': return self.superscript
        if char == '_': return self.subscript
        if char == '~': return self.active
        if char == '%': return self.comment
        return self.other

    new_line = 0
    skipping = 1
    middle = 2

    def __init__(self, inp=''):
        self.state = self.new_line
        self.catcode = self.CatcodeMapStack()
        self.definitions = MapStack()
        self.tokens = []
        self.line = ''
        self.input = inp
        self.condition_level = 0
        self.populate_with_default_macros()

        self.line_num = 0
        self.file = ''

        self.token_state = []

        def size(): return len(self.tokens)
        def get(idx): return self.tokens[idx]
        def populate(): return self.tokenize() # self.step_rules('tokenizer')
        self.autotokens = self.T(size, get, populate)

        self.expanded_tokens = []
        self.noexpand_followed_by = None
        self.no_expand = False
        def esize(): return len(self.expanded_tokens)
        def eget(idx): return self.expanded_tokens[idx]
        def epopulate():
            while True:
                t = self.autotokens[0]
                if t[1] == self.control_sequence and not self.no_expand:
                    if t[0] in self.definitions:
                        self.expand()
                    else:
                        raise TeXError("Undefined macro encountered `%s'" % t[0])
                elif t[1] == self.active:
                    if (t[0],) in self.definitions:
                        self.expand()
                    else:
                        raise TeXError("Undefined active character encountered `%s'" % t[0])
                else:
                    if t == self.noexpand_followed_by:
                        self.no_expand = True
                    else:
                        self.no_expand = False
                    self.expanded_tokens.append(t)
                    self.tokens = self.tokens[1:]
                    # print(self.expanded_tokens)
                    break
        self.autoexpandtokens = self.T(esize, eget, epopulate)

        # Define user macros
        self.define_macros()

    def populate_with_default_macros(self):
        self.definitions['def'] = self.Functional([], [('def', self.command)])
        self.definitions['let'] = self.Functional([], [('let', self.command)])
        # self.definitions['def'] = ([], [('def', self.command)])
        self.definitions['par'] = self.Functional([], [('par', self.command)])
        self.definitions['char'] = self.Functional([], [('char', self.command)])
        self.definitions['catcode'] = self.Functional([], [('catcode', self.command)])
        self.definitions['relax'] = self.Builtin('relax')
        self.definitions[' '] = self.Functional([], [(' ', self.space)])
        for c in '%#@!`~${}^&*': self.definitions[c] = self.Functional([], [(c, self.other)])

        # TODO: { } and \begin and \endgroup should not mix
        # self.definitions['begingroup'] = self.Functional([], [('{', self.begin_group)])
        # self.definitions['endgroup'] = self.Functional([], [('{', self.end_group)])

        self.definitions['input'] = self.Functional([], [('input', self.command)])
        self.definitions['endinput'] = self.Functional([], [('endinput', self.command)])

        self.definitions['ifx'] = self.Builtin('ifx')
        self.definitions['iftrue'] = self.Builtin('iftrue')
        self.definitions['iffalse'] = self.Builtin('iffalse')
        self.definitions['else'] = self.Builtin('else')
        self.definitions['fi'] = self.Builtin('fi')

        self.definitions['ifTeXP'] = self.definitions['iftrue']

        self.definitions['csname'] = self.Builtin('csname')
        self.definitions['endcsname'] = self.Builtin('endcsname')

        self.definitions['expandafter'] = self.Builtin('expandafter')

    def print_state(self):
        print()
        print('State:', self.state)
        print('Tokens:', str(self.tokens))
        print('Line:', self.line[0:20], '...')
        print('Input:', self.input[0:20], '...')

    def tokenizer_read_line(self):
        if self.line == '' and len(self.input) > 0:
            i = self.input.find('\n')
            if i >= 0:
                k = i
                for j in range(i - 1, -1, -1):
                    if not (self.input[j] == ' '):
                        k = j + 1
                        break
                self.line = self.input[0:k] + '\n'
                self.input = self.input[i+1:]
            else:
                self.line = self.input
                self.input = ''
            self.state = self.new_line
            self.line_num += 1
            return True
        return False

    __rules__['tokenizer'].append(tokenizer_read_line)


    def tokenize_control_code(self):
        # if len(self.line) > 0: print (self.line[0])
        if len(self.line) > 0 and self.catcode[self.line[0]] == self.escape:
            k = 1
            for i in range(1, len(self.line)):
                if self.catcode[self.line[i]] != self.letter:
                    break 
                k = i
            self.tokens.append( (self.line[1:k+1], self.control_sequence) )
            self.line = self.line[k+1:]
            self.state = self.skipping
            return True
        return False

    __rules__['tokenizer'].append(tokenize_control_code)

    def tokenizer_scan_char(self):
        if len(self.line) > 0 and self.catcode[self.line[0]] in (1, 2, 3, 4, 6, 7, 8, 11, 12, 13):
            self.state = self.middle
            self.tokens.append( (self.line[0], self.catcode[self.line[0]]) )
            self.line = self.line[1:]
            return True
        return False

    __rules__['tokenizer'].append(tokenizer_scan_char)

    def tokenizer_scan_space(self):
        if len(self.line) > 0 and self.catcode[self.line[0]] == self.space:
            if self.state == self.middle:
                self.tokens.append( (' ', self.space) )
                self.state = self.skipping
            self.line = self.line[1:]
            return True
        return False

    __rules__['tokenizer'].append(tokenizer_scan_space)

    def tokenizer_scan_newline(self):
        if len(self.line) > 0 and self.catcode[self.line[0]] == self.end_of_line:
            if self.state == self.new_line:
                self.tokens.append( ('par', self.control_sequence) )
            elif self.state == self.middle:
                self.tokens.append( (' ', self.space) )
                self.state = self.new_line
            self.line = ''
            return True
        return False

    __rules__['tokenizer'].append(tokenizer_scan_newline)

    def tokenizer_scan_ignore(self):
        if len(self.line) > 0 and self.catcode[self.line[0]] == self.ignored:
            self.line = self.line[1:]
            return True
        return False

    __rules__['tokenizer'].append(tokenizer_scan_ignore)

    def tokenizer_scan_invalid(self):
        if len(self.line) > 0 and self.catcode[self.line[0]] == self.invalid:
            self.line = self.line[1:]
            raise InvalidCharacter()
            # return True
        return False

    __rules__['tokenizer'].append(tokenizer_scan_invalid)

    def tokenizer_scan_comment(self):
        if len(self.line) > 0 and self.catcode[self.line[0]] == self.comment:
            self.line = ''
            return True
        return False

    __rules__['tokenizer'].append(tokenizer_scan_comment)

    def command_command(self):
        if len(self.tokens) > 0 and self.tokens[0][1] == self.command and self.tokens[0][0] in self.__commands__:
            cmd = self.__commands__[self.tokens[0][0]]
            cmd(self)
            return True
        return False

    __rules__['command'].append(command_command)

    def command_unknown_command(self):
        if len(self.tokens) > 0 and self.tokens[0][1] == self.command and not self.tokens[0][0] in self.__commands__:
            cmd = self.tokens[0][0]
            self.tokens = self.tokens[1:]
            if not self.process_command(cmd):
                raise TeXError("Unknown primitive `%s'" % cmd)
            return True
        return False

    __rules__['command'].append(command_unknown_command)


    def command_def(self):
        if len(self.tokens) > 0 and self.tokens[0] == ('def', self.command):
            ts  = self.autotokens
            c = None
            try:
                if ts[1][1] == self.control_sequence:
                    c = ts[1][0]
                elif ts[1][1] == self.active:
                    c = (ts[1][0],)
                else:
                    raise TeXError("Control sequence (macro) expected but `%s' found" % ts[1][0])
                k = -1
                i = 2
                while True:
                    if ts[i][1] == self.begin_group:
                        k = i - 1
                        break
                    i += 1
                if k < 0 : return False # did not match

                g = 0
                b = - 1
                i = k+1
                while True:
                    if ts[i][1] == self.begin_group: g = g + 1
                    elif ts[i][1] == self.end_group: g = g - 1
                    if g == 0: 
                        b = i
                        break
                    i += 1
                if b < 0: return False # did not match
            except IndexError:
                return False

            def reduce_params(toks):
                n = []
                i = 0
                while i < len(toks):
                    if i + 1 < len(toks) and toks[i][1] == self.param and toks[i+1][1] == self.other:
                        n.append( (toks[i+1][0], self.parameter) )
                        i = i + 2
                    else:
                        n.append( toks[i] )
                        i = i + 1
                return n
            
            # T does not support slice objects, (shoud I add it?)
            ts = self.tokens

            params = reduce_params(ts[2:k+1])
            body = reduce_params(ts[k+2:b])

            seq = [ int(x) for x, c in params if c == self.parameter]
            if not seq == list(range(1, len(seq)+1)): raise TeXError()

            bodyparam = [ int(x) for x, c in body if c == self.parameter]
            if not set(bodyparam).issubset(set(seq)): raise TeXError()

            self.definitions[c] = self.Functional(params, body)
            self.tokens = ts[b+1:]
            return True
        return False

    __commands__['def'] = command_def


    def expander_macro_not_defined(self):
        if len(self.tokens) > 0 and self.tokens[0][1] == self.control_sequence and not (self.tokens[0][0] in self.definitions):
            # print ("Definition not found", self.tokens[0][0])
            raise TeXError("Macro `%s' is not defined on line %d of file %s." % (self.tokens[0][0], self.line_num, self.file))
        return False

    __rules__['command'].append(expander_macro_not_defined)

    def expander_expand_macro(self):
        if (len(self.tokens) > 0 
            and ((self.tokens[0][1] == self.control_sequence 
                 and self.tokens[0][0] in self.definitions
                 and isinstance(self.definitions[self.tokens[0][0]], self.Functional))
                 or
                 (self.tokens[0][1] == self.active
                 and (self.tokens[0][0],) in self.definitions
                 and isinstance(self.definitions[(self.tokens[0][0],)], self.Functional)))
            ):

            t = self.tokens[0]
            if t[1] == self.active:
                res = (t[0],)
            else:
                res = t[0]

            # (params, body) = self.definitions[self.tokens[0][0]]
            (params, body) = self.definitions[res]
            def next_token_or_group(ts, i):
                g = 0
                if ts[i][1] == self.begin_group:
                    b = -1
                    while True:
                        if ts[i][1] == self.begin_group: g = g + 1
                        elif  ts[i][1] == self.end_group: g = g - 1
                        if g == 0: 
                            b = i
                            break
                        i += 1
                    return b
                else:
                    return i

            def find(arr, i, f, notfound=-1):
                for j in range(i, len(arr)):
                    if f(arr[j]):
                        return j
                return notfound

            p = 0
            i = 1
            matched = []
            try:
                while p < len(params):
                    # if it is a non-delimeted parameter
                    if params[p][1] == self.parameter and (p+1 == len(params) or params[p+1][1] == self.parameter):
                        j = next_token_or_group(self.autotokens, i)
                        # TODO: also possibly match optional spaces
                        if j < 0: return False
                        # print(j-i)
                        if j - i > 0: # strip the group tokens
                            matched.append(self.autotokens[i+1:j])
                        else:
                            matched.append(self.autotokens[i:j+1])
                        i = j+1
                        p = p+1
                    # if it is a delimited parameter
                    elif params[p][1] == self.parameter:
                        k = find(params, p+1, lambda x: x[1] == self.parameter, len(params))
                        tomatch = params[p+1:k]
                        j = i
                        m = False
                        # while j < len(self.tokens):
                        while True:
                            if tomatch == self.autotokens[j:j+len(tomatch)]:
                                m = True
                                break
                            j = next_token_or_group(self.tokens, j) + 1
                        if not m: return False
                        matched.append(self.tokens[i:j])
                        i = j + len(tomatch)
                        p = k
                    else:
                        k = find(params, p, lambda x: x[1] == self.parameter, len(params))
                        if params[p:k] == self.autotokens[i:i+k]:
                            p += k
                            i += k
                        else:
                            return False
            except IndexError:
                return False
            
            # print(matched)
            expansion = []
            for t in body:
                if t[1] == self.parameter:
                    expansion.extend(matched[int(t[0])-1])
                else:
                    expansion.append(t)

            # print(expansion)

            self.tokens = expansion + self.tokens[i:]
            return True
        return False

    __rules__['expander'].append(expander_expand_macro)

    def isbuiltin(self, token, type):
        return (token[1] == self.control_sequence and token[0] in self.definitions 
                and self.definitions[token[0]] == self.Builtin(type))

    def isconditional(self, token):
        conditionals = ('ifx', 'iftrue', 'iffalse')
        return exists(lambda x: self.isbuiltin(token, x), conditionals)


    def expander_conditional(self):
        if (len(self.tokens) > 0 and self.tokens[0][1] == self.control_sequence
            and self.tokens[0][0] in self.definitions
            and isinstance(self.definitions[self.tokens[0][0]], self.Builtin)):

            type = self.definitions[self.tokens[0][0]][0]
            ts = self.autotokens

            cond = False
            i = 1

            if type == 'ifx':
                try:
                    a = ts[1]
                    b = ts[2]
                    cond = ((a == b) or 
                        (a[1] == self.control_sequence and b[1] == self.control_sequence and
                        a[0] in self.definitions and b[0] in self.definitions and
                        self.definitions[a[0]] == self.definitions[b[0]]))
                    i = 3
                    # print(self.tokens[i:i+20])
                except IndexError:
                    return False
            elif type == 'iftrue':
                cond = True
            elif type == 'iffalse':
                cond = False
            else:
                # Not a conditional builtin macro
                return False

            # print(cond)
            self.condition_level += 1
            # true branch, continue expanding
            try:
                if not cond: # False branch, skip to \else or \fi
                    level = 0
                    while True:
                        if self.isconditional(ts[i]):
                            level +=1
                        elif self.isbuiltin(ts[i], 'else') and level == 0:
                            i += 1
                            break
                        elif self.isbuiltin(ts[i], 'fi'):
                            if level == 0: break
                            else: level -= 1
                        i += 1
            except IndexError:
                return False

            self.tokens = self.tokens[i:]
            return True
        return False

    __rules__['expander'].append(expander_conditional)

    def expand_else(self):
        if len(self.tokens) > 0 and self.isbuiltin(self.tokens[0], 'else'):
            if self.condition_level == 0:
                raise TeXError("Lone \\else scanned")
            ts = self.autotokens
            # skip to \fi
            i = 1
            level = 0
            try:
                while True:
                    if self.isconditional(ts[i]):
                        level +=1
                    elif self.isbuiltin(ts[i], 'fi'):
                        if level == 0: break
                        else: level -= 1
                    i += 1
            except IndexError:
                return False

            self.condition_level -= 1
            self.tokens = self.tokens[i+1:]

            return True
        return False

    __rules__['expander'].append(expand_else)

    def expand_fi(self):
        if len(self.tokens) > 0 and self.isbuiltin(self.tokens[0], 'fi'):
            self.tokens = self.tokens[1:]
            if self.condition_level == 0:
                raise TeXError("Lone \\fi scanned.")
            self.condition_level -= 1
            return True
        return False

    __rules__['expander'].append(expand_fi)

    def expand_relax(self):
        if len(self.tokens) > 0 and self.isbuiltin(self.tokens[0], 'relax'):
            self.tokens = self.tokens[1:]
            return True
        return False

    __rules__['expander'].append(expand_relax)

    def expand_expandafter(self):
        if len(self.tokens) > 0 and self.isbuiltin(self.tokens[0], 'expandafter'):
            ts = self.autotokens
            t = ts[1] # the token to skip
            _ = ts[2] # read after the first token to trigger tokenisation
            self.tokens = self.tokens[2:]
            self.expand()
            self.tokens = [t] + self.tokens
            return True
        return False

    __rules__['expander'].append(expand_expandafter)


    def expand_csname(self):
        if len(self.tokens) > 0 and self.isbuiltin(self.tokens[0], 'csname'):
            self.tokens = self.tokens[1:]
            ts = self.autotokens
            toks = []
            while True:
                if self.isbuiltin(ts[0], 'endcsname'):
                    self.tokens = self.tokens[1:]
                    break
                if ts[0][1] == self.control_sequence:
                    if ts[0][0] in self.definitions:
                        self.expand()
                    else:
                        raise TeXError("Undefined control sequence `%s'" % ts[0][0])
                elif ts[0][1] == self.command:
                    raise TeXError("Primitve command found `%s' while processing \\csname." % ts[0][0])
                else:
                    toks.append(ts[0][0])
                    self.tokens = self.tokens[1:]

            name = ''.join(toks)
            if not name in self.definitions:
                self.definitions[name] = self.Builtin('relax')

            self.tokens.insert(0, (name, self.control_sequence))
            return True
        return False

    __rules__['expander'].append(expand_csname)


    def command_open_group(self):
        if len(self.tokens) > 0 and self.tokens[0][1] == self.begin_group:
            self.definitions.push()
            self.tokens = self.tokens[1:]
            return True
        return False

    __rules__['command'].append(command_open_group)

    
    def command_close_group(self):
        if len(self.tokens) > 0 and self.tokens[0][1] == self.end_group:
            self.definitions.pop()
            self.tokens = self.tokens[1:]
            return True
        return False

    __rules__['command'].append(command_close_group)

    def command_token(self):
        if len(self.tokens) > 0 and self.tokens[0][1] in (0, 3, 4, 5, 6, 7, 8, 10, 11, 12):
            self.process_token(self.tokens[0])
            self.tokens = self.tokens[1:]
            return True
        return False
    
    __rules__['command'].append(command_token)

    def save_token_state(self):
        self.token_state.append( (self.tokens, self.line, self.input, self.line_num, self.file) )

    def restore_token_state(self):
        (t, l, i, n, f) = self.token_state.pop()
        self.tokens = t
        self.line = l
        self.input = i
        self.line_num = n
        self.file = f

    def command_input(self):
        self.tokens = self.tokens[1:]
        ts = self.autotokens
        file = []
        # scan filename while expanding controll sequences
        while True:
            if ts[0][1] == self.space:
                self.tokens = self.tokens[1:]
                break
            elif ts[0][1] == self.command:
                break
            elif ts[0][1] == self.control_sequence:
                self.expand()
            else:
                file.append(ts[0][0])
                self.tokens = self.tokens[1:]

        filename = ''.join(file)

        try:
            handle = open(filename, 'r')
            self.save_token_state()
            self.tokens = []
            self.line = ''
            self.input = handle.read()
            self.line_num = 0
            self.file = filename
            handle.close()
        except FileNotFoundError:
            raise TeXError("File not found `%s'" % filename)

    __commands__['input'] = command_input

    def command_endinput(self):
        self.tokens = self.tokens[1:]
        if len(self.token_state) > 0:
            self.restore_token_state()
        else:
            self.tokens = []
            self.input = ''
            self.line = ''

    __commands__['endinput'] = command_endinput

    def command_input_ended(self):
        if self.tokens == [] and self.input == '' and self.line == '' and len(self.token_state) > 0:
            self.restore_token_state()
            return True
        return False

    __rules__['command'].append(command_input_ended)

    def command_par(self):
        self.tokens = self.tokens[1:]
        self.process_par()

    __commands__['par'] = command_par

    def command_char(self):
        rules = [
            ('`', [lambda t: t[0] == '`'], lambda x : None),
            ('t', [lambda t: True], lambda x: x[0][0]),
            ('d', [lambda t: t[0].isnumeric()], lambda x: x[0][0]),
            (' ', [lambda t: t[1] == self.space], lambda x : None),
            (' ', [], lambda x: None),
            ('n', ['d', 'n'], lambda x: x[0] + x[1]),
            ('n', ['d'], lambda x: x[0]),
            ('char', '`t ', lambda x: x[1]),
            ('char', 'n ', lambda x: chr(int(x[0]))),
        ]
        res = recursive_descent_matcher(rules, 'char', 1, self.autotokens)
        if res == None:
            raise TeXError("Failed to parse a character number")

        (r, i) = res
        
        if (len(r) > 1):
            raise TeXError("A single charecter control sequence is expected")

        self.tokens = [(r, self.other)] + self.tokens[i:]

    __commands__['char'] = command_char

    def command_catcode(self):
        rules = [
            ('`', [lambda t: t[0] == '`'], lambda x : None),
            ('=', [lambda t: t[0] == '='], lambda x : None),
            ('t', [lambda t: True], lambda x: x[0][0]),
            (' ', [lambda t: t[1] == self.space], lambda x : None),
            (' ', [], lambda x: None),
            ('d', [lambda t: t[0].isnumeric()], lambda x: x[0][0]),
            ('n', ['d', 'n'], lambda x: x[0] + x[1]),
            ('n', ['d'], lambda x: x[0]),
            ('i', 'n ', lambda x: int(x[0])),
            ('catcode', '`t=i ', lambda x: (x[1], x[3]))
        ]
        self.noexpand_followed_by = ('`', self.other)
        self.tokens = self.tokens[1:]
        res = recursive_descent_matcher(rules, 'catcode', 0, self.autoexpandtokens)
        self.noexpand_followed_by = None
        if res == None:
            raise TeXError("Failed to parse a catcode")

        ((t,n), i) = res
        
        if (len(t) > 1):
            raise TeXError("A single charecter control sequence is expected")

        if n > 15:
            raise TeXError("Unknown category code %d" % n)

        self.catcode[t] = n

        leftover = self.expanded_tokens[i:]
        self.tokens = leftover + self.tokens
        self.expanded_tokens = []


    __commands__['catcode'] = command_catcode

    def command_let(self):

        ts = self.autotokens

        cs = ts[1]
        eq = ts[2]
        t = ts[3]

        # TODO cs could be also active character
        if not cs[1] == self.control_sequence:
            raise TeXError("Control sequence expected while handling \\let")

        if not eq[0] == '=':
            raise TeXError("Character = expected while handling \\let")

        if t[1] == self.control_sequence:
            if t[0] in self.definitions:
                self.definitions[cs[0]] = self.definitions[t[0]]
            else:
                # TODO: should be undefined for the current group level
                self.definitions[cs[0]] = None
        else:
            raise TeXError("Other than control sequences are currently not handled by \\let")

        self.tokens = self.tokens[4:]

    __commands__['let'] = command_let

    def define_macros(self):
        pass

    def process_token(self, token):
        print (token[0], end='')
        # raise NotImplementedError
        
    def process_command(self, cmd):
        print("Command", cmd)
        return False

    def process_par(self):
        print()

    def define_command_macro(self, cmd):
        self.definitions[cmd] = self.Functional([], [(cmd, self.command)])



class TeXOutputStdout(TeX):

    def define_macros(self):
        pass
        # # cmds = ('tagOpen', 'tagClose', 'tagEndOpen', 'tagEndClose')
        # for c in cmds:
        #     self.define_command_macro(c)

    def process_par(self):
        print()

    def process_token(self, t):
        c = t[0]
        print(c, sep='', end='')

    def process_command(self, cmd):
        return False


if __name__ == "__main__":
    import sys
    file = sys.argv[1]
    f = open(file, 'r')
    content = f.read()
    f.close()
    t = TeXOutputStdout(content)
    t.run()


# t = TeX("\\xyz{}\\def\\hello#1 #2{world #2} hello { xx }  \\code x \n\n  \n\n, w\norld!")
# t = TeX("\\def\\hello#1 #2{world #2} hello { xx }  %\\code x \n\n  \n\n, w\norld!")
# t = TeX("\\def\\hello\\start{START}\\hello\\start")
# t = TeX("\\def\\hello \\start #1 \\middle #2\\end{(#1,#2)}\\hello \\start this is a start \\middle more in the middle \\end")
# t = TeX("\\def\\hello#1{#1}\\hello{2}A")
# t = TeX("\\def\\hello#1\\end{#1}\\hello x\\end\n\nLabas")
# t = TeX("\\def\\hello#1\\end{#1}\\hello x\\end\n\nLabas")
# t = TeX("\\else")
# t = TeX("\\def\\x{1}\\def\\y{1}\\ifx\\ifx\\ifx Yes\\else No\\fi")
# t = TeX("\\def\\ifempty#1#2#3{\\def\\a{#1}\\def\\b{}\\ifx\\a\\b #2\\else #3\\fi}\\ifempty{ }{YES}{NO}")
# t = TeX("\\iftrue Yes\\fi")
# t = TeX("\\iftrue \\iftrue Hello\\else\\else\\else Not Hello\\fi Hello World\\else False\\fi |")
# t = TeX("\\csname Hello\\endcsname\\def\\Hello{x}\\ifx\\Hello\\relax YES\\else XX\\fi")
# t = TeX("\char`\hHello")
# t = TeX("\\def~#1#2{Hell(#1,#2)} ~ab")
# t = TeX("\\relax")
# t = TeX("\\expandafter\\def\\csname Hello\\endcsname{World}\\Hello")
# t = TeX("\\def\\Foo{Bar}\\expandafter \\Boo \\expandafter \\Boo \\Foo")
# t = TeX("\\def\\a{Hello}\\let\\b=\\c \\b")
# t = TeX("\\catcode`\\@=11 \\def\\@hello@{Hello, World}\\@hello@")
# t.run()
# t.run()
# print()
# print(t.line, '|', sep='')
# print(t.input, '|', sep='')
# print(t.tokens)




