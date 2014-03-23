# PyFlo - Flow-Based Programming for Python
# Copyright (c) 2014 Jon Nordby <jononor@gmail.com>
# PyFlo may be freely distributed under the MIT license
##

import sys, os
import functools
import json
import subprocess

sys.setrecursionlimit(100)

class Port(object):
    def __init__(self):
        self.target = None
        self.value = None

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

class Nary(Component):
    @staticmethod
    def factory(inports, func):
        return functools.partial(Nary, inports, func)

    def __init__(self, inports, function):
        Component.__init__(self)
        self._func = function
        self.ports = {
            "out": Port()
        }
        self._inports = inports
        for name in inports:
            self.ports[name] = Port()

    def receive(self, data, port):
        # Store new data for @port
        p = self.ports.get(port, None)
        if not p:
            raise ValueError, 'No port named %s in Nary(X)' % port
        p.value = data

        # Re-evaluate function
        # TODO: allow None?
        args = [self.ports[n].value for n in self._inports]
        if not any(x is None for x in args):
            res = self._func(*args)
            self.send(res, "out")

components = {
    "Invert": Unary.factory(lambda obj: not obj),
    "IncrementOne": Unary.factory(lambda obj: obj+1),
    "WriteStdOut": Unary.factory(lambda obj: sys.stdout.write(obj)),
    "Str": Unary.factory(lambda obj: str(obj)),

    "Add": Nary.factory(["a", "b"], lambda a,b: a+b),
    "Subtract": Nary.factory(["a", "b"], lambda a,b: a-b),
    "Multiply": Nary.factory(["a", "b"], lambda a,b: a*b),
    "Divide": Nary.factory(["a", "b"], lambda a,b: a/b),
}

def map_literal(data):
    converters = [
        lambda d: int(data),
        lambda d: float(data),
        lambda d: d,
    ]
    for conv in converters:
        try:
            return conv(data)
        except (ValueError, TypeError), e:
            continue

    raise Error, 'Should never be reached'

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
            data = map_literal(data)
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
        # TODO: implement natively. Using pyPEG/grako?
        s = subprocess.check_output(["fbp", path])
        return json.loads(s)
    elif ext == ".json":
        f = open(path, "r")
        return json.loads(f.read())
    else:
        raise ValueError, "Invalid format for file %s" % path


from autobahn.websocket import WebSocketServerProtocol, WebSocketServerFactory
from twisted.python import log
from twisted.internet import reactor

class MyServerProtocol(WebSocketServerProtocol):

    def onConnect(self, request):
        pass

    def onOpen(self):
        pass

    def onClose(self, wasClean, code, reason):
        pass

    def onMessage(self, payload, isBinary):
        if isBinary:
            raise ValueError, "WebSocket message must be UTF-8"

        cmd = json.loads(payload)
        print cmd

        if cmd['protocol'] == 'component' and cmd['command'] == 'list':
            for name, comp in components.items():
                payload = { "name": name,
                        "description": "",
                        "inPorts": [ {"id": "in", "type": "all" } ],
                        "outPorts": [ {"id": "out", "type": "all" } ],
                }
                resp = {"protocol": "component",
                    "command": "component",
                    "payload": payload,
                }
                self.sendMessage(json.dumps(resp))


def runtime():
    log.startLogging(sys.stdout)

    factory = WebSocketServerFactory("ws://localhost:3569", debug = False)
    factory.protocol = MyServerProtocol

    reactor.listenTCP(3569, factory)
    reactor.run()

#runtime()


if __name__ == "__main__":

    prog, args = sys.argv[0], sys.argv[1:]
    if not len(args) == 1:
        sys.stderr.write("Usage: %s FILE\n" % prog)
        sys.exit(1)

    path = args[0]

    net = Network(load_file(path))
    net.start()
    net.run_iteration()

