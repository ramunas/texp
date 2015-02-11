#!/usr/bin/env python3

from texp import *


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



def process(stream, page, top=False):
    for i in stream:
        if is_controlsequence(i):
            # tag{name}{{attrname}{val}...}{content}
            if i.name == 'tag':
                name = tokenstream_to_str(next_token_or_group(stream))
                attributes = next_token_or_group(stream)
                attrs = split_attrs(iter(attributes))
                content = next_token_or_group(stream)

                attrstring = ''
                for i in attrs:
                    attrstring = attrstring + (' %s="%s"' % (tokenstream_to_str(iter(i[0])), tokenstream_to_str(iter(i[1]))))

                page.send('<%s%s>' % (name, attrstring))
                process(content, page)
                page.send('</%s>' % name)
            elif i.name == 'par':
                page.send("\n\n")
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
        else:
            page.send(i.tok)

def main():
    s = expand(resetable(tokenstream(resetable(bytestream('main.tex')))))
    process(s, new_page('index.html'), True)


if __name__ == '__main__':
    main()

