
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


class parser:
    "Monadic parser"

    def __init__(self, val=None):
        # an always suceeding parser
        self.__action__ = lambda s: ((val,),s)

    def __bind__(self, prs, f):
        def action(stream):
            v, s = prs.parse(stream)
            if v is not None:
                v, = v
                return f(v).parse(s)
            else:
                return None, s
        p = parser()
        p.__action__ = action
        return p

    def __unit__(self, e):
        p = parser()
        p.__action__ = lambda s: ((e,), s)
        return p

    def __sat__(self, pred):
        def action(s):
            v, s = s.next()
            if v is None:
                return None, s
            if pred(v):
                return (v,), s
            return None, s
        p = parser()
        p.__action__ = action
        return p

    def __next__(self):
        return self.__sat__(lambda x: True)

    def __choice__(self, prs1, prs2):
        def action(s):
            v,s2 = prs1.parse(s)
            if v is None:
                return prs2.parse(s)
            return v,s2
        p = parser()
        p.__action__ = action
        return p

    def __fail__(self):
        p = parser()
        p.__action__ = lambda s: None, s
        return p

    def parse(self, s):
        return self.__action__(s)


    def bind(self, f):
        return self.__bind__(self, f)

    def next(self):
        return self.__bind__(self, lambda _: self.__next__())

    def sat(self, p):
        return self.__bind__(self, lambda _: self.__sat__(p))

    def unit(self, v):
        return self.__bind__(self, lambda _: self.__unit__(v))

    def alt(self, prs):
        return self.__choice__(self, prs)


    fail = __fail__
    choice = __choice__

