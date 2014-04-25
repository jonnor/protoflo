ProtoFlo
======
Experiments in dataflow and Flow-based programming based on Python,
compatible and integrated with [NoFlo](http://noflojs.org)

Installing
======
After having Python 2.7 installed:
```
sudo easy_install -U setuptools
sudo easy_install autobahn
sudo easy_install twisted
```

Running
======
1. Register ProtoFlo as a NoFlo runtime (discover what is your UID
   on NoFlo)
   ```
   python protoflo.py register --user YOUR_UID --label ProtoFlo
   ```
2. Run ProtoFlo
   ```
   python protoflo.py runtime
   ```
3. Create a new project on NoFlo selecting the ProtoFlo runtime
4. Inside the new project/graph, select the appropriate ProtoFlo
   runtime clicking on the top-right menu
5. Green arrows should appear on the top-right menu, right before
   `ws:\\localhost:3569`
6. Try typing `Add` into the component search box on top-left

Status
=======
Prototyping

Can run simple graphs defined by NoFlo .fbp and .json,
can enumerate its components using the NoFlo UI protocol.

License
=======
MIT


TODO:
======
* Allow to build/run graphs using NoFlo UI protocol.
* Write tests
* Implement components for glib/GI, incl mainloop. GTK+ example
* Implement port2port NoFlo Websocket protocol
* Implement MicroFlo serial-protocol components

