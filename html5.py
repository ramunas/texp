#!/usr/bin/env python3

import texp
from texp import *
import itertools
import datetime
import os


class new_page(object):
    counter = 0

    def __init__(self, name=None):
        self.name = name
        if name == None:
            genname = 'page%d.html' % new_page.counter
            new_page.counter = new_page.counter + 1
            self.fd = open(genname,'w')
        else:
            self.fd = open(name,'w')

        self.send("<!DOCTYPE html>")

    def send(self,s):
        self.fd.write(s)

    def close(self):
        self.fd.close()


def split_attrs(stream):
    attrs = []
    try:
        while True:
            (stream, x) = next_token_or_group(stream)
            attrs.append(x)
    except StopIteration:
        pass

    r = []
    t = []
    for i in attrs:
        t.append(i)
        if len(t) == 2:
            r.append(t)
            t = []

    if len(t) != 0:
        t.append([])
        r.append(t)

    return r



def tag(stream):
    (stream, tokens) = next_token_or_group(stream)
    name = tokenstream_to_str(tokens)
    (stream, attributes) = next_token_or_group(stream)
    attrs = split_attrs(iter(attributes))

    attrstring = ''
    for i in attrs:
        attrstring = attrstring + (' %s="%s"' % (tokenstream_to_str(iter(i[0])), tokenstream_to_str(iter(i[1]))))
    return (stream, name, attrstring)

def process(stream, page, top=False):
    while True:
        i = next(stream, None)
        if i == None:
            break

        if is_controlsequence(i):
            # tag{name}{{attrname}{val}...}{content}
            if i.name == 'tag':
                (stream, name, attrstring) = tag(stream)
                (stream, content) = next_token_or_group(stream)

                page.send('<%s%s>' % (name, attrstring))
                process(iter(content), page)
                page.send('</%s>' % name)
            elif i.name == 'opentag':
                (stream, name, attrstring) = tag(stream)
                page.send('<%s%s>' % (name, attrstring))
            elif i.name == 'openclosetag':
                (stream, name, attrstring) = tag(stream)
                page.send('<%s%s/>' % (name, attrstring))
            elif i.name == 'closetag':
                (stream, tokens) = next_token_or_group(stream)
                name = tokenstream_to_str(tokens)
                page.send('</%s>' % name)
            elif i.name == 'par':
                page.send("\n\n")
            elif i.name == 'htmlnewline':
                page.send("\n\n")
            elif i.name == 'currentdate':
                page.send(str(datetime.datetime.now().date()))
            elif i.name == 'newnamedpage':
                (stream, tokens) = next_token_or_group(stream)
                name = tokenstream_to_str(tokens)
                if top == True:
                    page.close()
                    page = new_page(name)
                else:
                    raise Exception("\\newnamedpage can only be used at the top level.")
            elif i.name == 'newpage':
                if top == True:
                    page.close()
                    page = new_page()
                else:
                    raise Exception("\\newpage can only be used at the top level.")
            elif i.name == 'ifempty': # this is a bit of a hack, I should add conditional macros to texp
                (stream, t) = next_token_or_group(stream)
                (stream, thn) = next_token_or_group(stream)
                (stream, els) = next_token_or_group(stream)
                if len(t) == 0:
                    process(iter(thn),page)
                else:
                    process(iter(els),page)
            elif i.name == 'includehtmlsnippet':
                (stream, tokens) = next_token_or_group(stream)
                filename = tokenstream_to_str(tokens)
                f = open(filename, 'r')
                content = f.read()
                page.send(content)
                f.close()
            else:
                raise Exception("Undefined macro %s" % i.name)
        else:
            if has_catcode(i, CatCode.begin_group):
                pass
            elif has_catcode(i, CatCode.end_group):
                pass
            elif i.tok == '~':
                page.send('&nbsp;')
            else:
                page.send(i.tok)


def expand(tokenstream):
    bm = defaultbuiltinmacros
    bm['environ'] = environ_macro()
    um = {}
    um['%'] = ([[]], [TokenCode('%', CatCode.other)])
    um['#'] = ([[]], [TokenCode('#', CatCode.other)])
    s = texp.expand(tokenstream, bm, um)
    return s


def make_builtin_macro(args, f):
    def macro (tokenstream, um):
        a = []
        for i in args:
            (tokenstream, x) = next_token_or_group(tokenstream)
            if i == 'e':
                a.append(list(expand(iter(x))))
            else:
                a.append(x)

        res = f(*a)
        return itertools.chain(iter(res), tokenstream)

    return macro

def environ_macro():
    def m(var):
        var = tokenstream_to_str(iter(var))
        res = os.environ.get(var)
        if res == None:
            raise TeXException("Undefined environement variable '%s'" % var)
        return [TokenCode(s, CatCode.letter) for s in res]
    return make_builtin_macro(['e'], m)


def read_file(file):
    f = open(file,'r')
    c = f.read()
    f.close()
    return c

def main():
    content = iter(read_file('main.tex'))
    s = expand(tokenstream(content))
    process(s, new_page('index.html'), True)



if __name__ == '__main__':
    main()

