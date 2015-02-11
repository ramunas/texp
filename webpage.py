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


def process(stream, page, top=False):
    for i in stream:
        if is_controlsequence(i):
            # tag{name}{attr=val,...}{content}
            if i.name == 'tag':
                name = tokenstream_to_str(next_token_or_group(stream))
                attributes = tokenstream_to_str(next_token_or_group(stream))
                content = next_token_or_group(stream)

                page.send('<%s>' % name)
                process(content, page)
                page.send('</%s>' % name)
            elif i.name == 'par':
                page.send("\n\n")
            elif i.name == 'newpage':
                if top == True:
                    page.close()
                    page = new_page()
                else:
                    raise Exception("\\newpage can only be used at the top level.")
        else:
            page.send(i.tok)

def main():
    s = expand(tokenstream(resetable(bytestream('main.tex'))))
    process(s, new_page('index.html'), True)


if __name__ == '__main__':
    main()

