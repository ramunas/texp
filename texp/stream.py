
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

