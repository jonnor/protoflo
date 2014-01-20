import sys, os
import functools
import json
import subprocess

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

components = {
    "Invert": Unary.factory(lambda obj: not obj),
    "IncrementOne": Unary.factory(lambda obj: obj+1),
    "WriteStdOut": Unary.factory(lambda obj: sys.stdout.write(obj)),
    "Str": Unary.factory(lambda obj: str(obj)),
}


class Network(object):
    def __init__(self, graph):
        self._graph = graph
        self.stop()

    def stop(self):
        self._state = "stopped"
        self._nodes = {}
        self._msgqueue = []

    def start(self):
        # Instantiate components
        graph = self._graph
        for name, data in graph['processes'].items():
            self._nodes[name] = components[data['component']]()

        # Wire up ports, IIPs
        for conn in graph['connections']:
            tgt = conn['tgt']
            src = conn.get('src', None)
            data = conn.get('data', None)
            if src:
                self.connect(src['process'], src['port'],
                             tgt['process'], tgt['port'])
            elif data is not None:
                iip = (tgt['process'], tgt['port'], data)
                self.send(*iip)
            else:
                raise ValueError, "No src node or IIP"
       

    def connect(self, src, srcport, tgt, tgtport):
        if not isinstance(src, Component):
            src = self._nodes[src]
        if not isinstance(tgt, Component):
            tgt = self._nodes[tgt]

        src.ports[srcport].target = (tgt, tgtport)
     
    def send(self, tgt, port, data):
        if not isinstance(tgt, Component):
            tgt = self._nodes[tgt]        

        ip = (tgt, port, data)
        self._msgqueue.append(ip)

    def _deliver_messages(self):
        stop_index = len(self._msgqueue)
        for index, msg in enumerate(self._msgqueue[0:stop_index]):
            if index == stop_index:
                break
            tgt, port, data = msg
            tgt.receive(data, port)
        self._msgqueue = self._msgqueue[stop_index:]

    def run_iteration(self):
        self._deliver_messages()

        

def load_file(path):
    ext = os.path.splitext(path)[1]
    if ext == ".fbp":
        # TODO: implement natively
        s = subprocess.check_output(["fbp", path])
        return json.loads(s)
    elif ext == ".json":
        f = open(path, "r")
        return json.loads(f.read())
    else:
        raise ValueError, "Invalid format for file %s" % path


def test2():
    net = Network(load_file("examples/first.fbp"))
    net.start()
    net.run_iteration()

if __name__ == "__main__":
    test2()
