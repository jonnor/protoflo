import sys, os
import functools

sys.setrecursionlimit(100)

class Port(object):
    def __init__(self):
        self.target = None

class Component(object):
    def __init__(self):
        self.ports = {}

    def receive(self, data, port):
        raise NotImplementedError

    def send(self, data, port):
        target = self.ports[port].target
        if target:
            tgtnode, tgtport = target
            tgtnode.receive(data, tgtport)
        else:
            pass

class Unary(Component):
    @staticmethod
    def factory(func):
        return functools.partial(Unary, func)

    def __init__(self, function):
        Component.__init__(self)
        self._func = function
        self.ports = {
            "in": Port(),
            "out": Port()
        }

    def receive(self, data, port):
        self.send(self._func(data), "out")

def connect(a, srcport, tgtport, b):
    a.ports[srcport].target = (b, tgtport)

def send(n, data):
    n.receive(data, "in")

Invert = Unary.factory(lambda obj: not obj)
IncrementOne = Unary.factory(lambda obj: obj+1)
WriteStdOut = Unary.factory(lambda obj: sys.stdout.write(obj))
Str = Unary.factory(lambda obj: str(obj))

# Test program
invert = Invert()
invert2 = Invert()
stringify = Str()
stdout = WriteStdOut()

connect(invert, "out", "in", invert2)
connect(invert2, "out", "in", stringify)
connect(stringify, "out", "in", stdout)

send(stdout, str(True))
send(stdout, "\n")
send(invert2, True)
send(stdout, "\n")
send(invert, True)
send(stdout, "\n")

# s
out = WriteStdOut()
inc = IncrementOne()
s = Str()
connect(inc, "out", "in", s)
connect(s, "out", "in", out)
send(inc, 1)
