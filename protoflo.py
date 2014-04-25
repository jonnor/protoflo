# ProtoFlo - Flow-Based Programming experiments in Python
# Copyright (c) 2014 Jon Nordby <jononor@gmail.com>
# ProtoFlo may be freely distributed under the MIT license
##

import sys, os
import functools
import json
import subprocess
import httplib
import uuid
import urllib

import numpy
from scipy import misc, ndimage
import matplotlib.pyplot as plt

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
    "Numpy/Array": Nary.factory(["values"], lambda values: numpy.asarray(values)),
    "Scipy/Lena": Nary.factory([], lambda: misc.lena()),
    "Scipy/GaussianFilter": Nary.factory(["array", "sigma"], lambda a, s: ndimage.gaussian_filter(a, sigma=s)),
    "Plot/ImageShow": Nary.factory(["array", "colormap"], lambda a,c: plt.imshow(a, cmap=c)),
    "Plot/Show": Nary.factory([], lambda: plt.show()),
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


from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from autobahn.websocket.compress import PerMessageDeflateOffer, PerMessageDeflateOfferAccept
from twisted.python import log
from twisted.internet import reactor


class NoFloUiProtocol(WebSocketServerProtocol):


    def onConnect(self, request):
        return 'noflo'

    def onOpen(self):
        self.sendPing()
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
                c = comp()
                # FIXME: separate outports from inports
                inports = [{ "id": p, "type": "all" } for p in c.ports.keys() if not p == "out"]
                payload = { "name": name,
                        "description": "",
                        "inPorts": inports,
                        "outPorts": [ {"id": "out", "type": "all" } ],
                }
                resp = {"protocol": "component",
                    "command": "component",
                    "payload": payload,
                }
                self.sendMessage(json.dumps(resp))


def runtime(port):
    log.startLogging(sys.stdout)

    factory = WebSocketServerFactory("ws://localhost:"+str(port), debug = True)
    factory.protocol = NoFloUiProtocol

    # Required for Chromium ~33 and newer
    def accept(offers):
        for offer in offers:
            if isinstance(offer, PerMessageDeflateOffer):
                return PerMessageDeflateOfferAccept(offer)
    factory.setProtocolOptions(perMessageCompressionAccept = accept)

    reactor.listenTCP(port, factory)
    reactor.run()

def register(user_id, label, ip, port):

    runtime_id = str(uuid.uuid4())

    conn = httplib.HTTPConnection("api.flowhub.io", 80)
    conn.connect()

    url = "/runtimes/"+runtime_id
    headers = {"Content-type": "application/json"}
    data = {
        'type': 'protoflo', 'protocol': 'websocket',
        'address': ip+":"+str(port), 'id': runtime_id,
        'label': label, 'port': port, 'user': user_id,
        'secret': "122223333",
    }

    conn.request("PUT", url, json.dumps(data), headers)
    response = conn.getresponse()
    if not response.status == 201:
        raise ValueError("Could not create runtime " + str(response.status) + str(response.read()))
    else:
        print "Runtime registered with ID", runtime_id

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(prog=sys.argv[0])
    subparsers = parser.add_subparsers(dest='command', help='')

    parser_register = subparsers.add_parser('register', help='Register runtime with Flowhub')
    parser_register.add_argument('--user', type=str, help='User UUID to register runtime for', required=True)
    parser_register.add_argument('--label', type=str, help='Label to use in UI for this runtime', default="ProtoFlo")
    parser_register.add_argument('--ip', type=str, help='WebSocket IP for runtime', default='ws://localhost')
    parser_register.add_argument('--port', type=int, help='WebSocket port for runtime', default=3569)

    parser_runtime = subparsers.add_parser('runtime', help='Start runtime')
    parser_runtime.add_argument('--port', type=int, help='WebSocket port for runtime', default=3569)

    args = parser.parse_args(sys.argv[1:])
    if args.command == 'register':
        register(args.user, args.label, args.ip, args.port)
    elif args.command == 'runtime':
        runtime(args.port)
    else:
        net = Network(load_file(path))
        net.start()
        net.run_iteration()

