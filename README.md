PyFlo
======
[Flow-based programming]() runtime for Python, compatible and integrated with [NoFlo](http://noflojs.org)

Status
=======
Prototyping

Can run simple graphs defined by NoFlo .fbp and .json,
can enumerate its components using the NoFlo UI protocol.

License
=======
MIT

Milestones
==========
0.0.1: "Proof of concept" Can instantiate and run a simple graph defined by .json
0.1.0: "Minimally useful" Can run a program based on some Python-tech which is not available for Node, integrated with NoFlo.

TODO:
======
* Allow to build/run graphs using NoFlo UI protocol.
* Write tests
* Implement components for glib/GI, incl mainloop. GTK+ example
* Implement port2port NoFlo Websocket protocol
* Implement MicroFlo serial-protocol components

