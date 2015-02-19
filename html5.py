#!/usr/bin/env python3

from texp import *
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
            x = next_token_or_group(stream)
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
    name = tokenstream_to_str(next_token_or_group(stream))
    attributes = next_token_or_group(stream)
    attrs = split_attrs(iter(attributes))

    attrstring = ''
    for i in attrs:
        attrstring = attrstring + (' %s="%s"' % (tokenstream_to_str(iter(i[0])), tokenstream_to_str(iter(i[1]))))
    return (name, attrstring)

def process(stream, page, top=False):
    for i in stream:
        if is_controlsequence(i):
            # tag{name}{{attrname}{val}...}{content}
            if i.name == 'tag':
                (name, attrstring) = tag(stream)
                content = next_token_or_group(stream)

                page.send('<%s%s>' % (name, attrstring))
                process(resetable(iter(content)), page)
                page.send('</%s>' % name)
            elif i.name == 'opentag':
                (name, attrstring) = tag(stream)
                page.send('<%s%s>' % (name, attrstring))
            elif i.name == 'openclosetag':
                (name, attrstring) = tag(stream)
                page.send('<%s%s/>' % (name, attrstring))
            elif i.name == 'closetag':
                name = tokenstream_to_str(next_token_or_group(stream))
                page.send('</%s>' % name)
            elif i.name == 'par':
                page.send("\n\n")
            elif i.name == 'htmlnewline':
                page.send("\n\n")
            elif i.name == 'currentdate':
                page.send(str(datetime.datetime.now().date()))
            elif i.name == 'newnamedpage':
                name = tokenstream_to_str(next_token_or_group(stream))
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
                t = next_token_or_group(stream)
                thn = next_token_or_group(stream)
                els = next_token_or_group(stream) 
                if len(t) == 0:
                    process(resetable(iter(thn)),page)
                else:
                    process(resetable(iter(els)),page)
            elif i.name == 'includehtmlsnippet':
                filename = tokenstream_to_str(next_token_or_group(stream))
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
            else:
                page.send(i.tok)



def read_file(file):
    f = open(file,'r')
    c = f.read()
    f.close()
    return c

def main():
    bm = defaultbuiltinmacros
    um = {}
    um['%'] = ([[]], [TokenCode('%', CatCode.other)])
    um['#'] = ([[]], [TokenCode('#', CatCode.other)])
    s = expand(resetable(tokenstream(resetable(bytestream('main.tex')))), bm, um)
    # content = iter(read_file('main.tex'))
    # s = expand(resetable(tokenstream(resetable(content))), bm, um)
    process(s, new_page('index.html'), True)



if __name__ == '__main__':
    main()

