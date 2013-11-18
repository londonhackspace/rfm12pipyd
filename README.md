
This is a python daemon that converts the serial data from a RMF12pi
to a webserver in a format sutable for grabbing with cacti

== How to add another node ==

Choose a nodeid and edit/compile/upload the firmware for your node.

In main.py add the nodeid to queues, the value should be a tuple with
the first item being a Queue.Queue() object and the 2nd a tuple of
strings, each of which is the name of a 16bit value that your node
sends on each update.

To get the data go to http://booch:12345/<nodeid>, you will get name:average
pairs for each value

e.g.

42: (Queue.Queue(), ('BeerTemp', 'AirTemp')),

would give you:

BeerTemp:3200 AirTemp:2200

from http://booch:12345/42 (assuming you are sending temp in centigrade * 100)

