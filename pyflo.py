import sys, os

sys.setrecursionlimit(10)

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
    def __init__(self, function):
        Component.__init__(self)
        self.ports = {
            "in": Port(),
            "out": Port()
        }
        self._func = function

    def receive(self, data, port):
        self.send(self._func(data), "out")

def connect(a, srcport, tgtport, b):
    a.ports[srcport].target = (b, tgtport)

def send(n, data):
    n.receive(data, "in")

# TODO: make these factories and not instances

invert = Unary(lambda obj: not obj)
add1 = Unary(lambda obj: obj+1)
stdout = Unary(lambda obj: sys.stdout.write(obj) )
stringify = Unary(lambda obj: str(obj))


connect(invert, "out", "in", stringify)
connect(stringify, "out", "in", stdout)

send(stdout, str(True))
send(stdout, "\n")
send(invert, True)
send(stdout, "\n")

