#!/usr/bin/env python

import serial, threading, Queue, time, logging, daemon
from logging.handlers import SysLogHandler
import BaseHTTPServer, urlparse, urllib
from pidfile import PidFile

class RFM12PIRx(threading.Thread):
  def __init__(self, port, queues):
    """Parse the records on the serial port and add them to queue
       for later use.
       
    Args:
      port (str): the serial port to use
      queues (dict): a dict of nodeid: (queue, labels)
        queue: the queue to append the results to
        labels: one for each of the 16 bit values to expect from the sensor
    """
    super(RFM12PIRx, self).__init__()
    self.s = serial.Serial(port, 9600)
    self.qs = queues
    self.setup(15,8,210)
    self.daemon = True

  def setup(self, baseid, frequency, group):
    self.s.write("%di" % (baseid))
    time.sleep(1)
    self.s.write("%db" % (frequency))
    time.sleep(1)
    self.s.write("%dg" % (group))
    time.sleep(1)
  
  def run(self):
    d = ""
    state = 0
    while True:
      data = self.s.read()
      if (ord(data) == 10 or ord(data) == 13) and len(d) > 0:
        d = d.strip()
        values = d.split(" ")
        d = ""
        if len(values) > 2:
          nodeid = int(values[0])
          values = values[1:]
          out = []
          for i in range(0, len(values), 2):
            # convert to 16 bit
            int16 = int(values[i]) + (int(values[i+1]) * 256)
            if (int16 > 32768):
              int16 = -65536 + int16
            out.append(int16)
          if nodeid in self.qs:
            self.qs[nodeid][0].put(out)
          else:
            logger.warn("unknown nodeid: %d : %s" % (nodeid, str(out)))
        else:
          logger.warn("wierd values: %s" % (str(values)))
      else:
        if ord(data) != 1:
          d = d + data

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
  def address_string(self):
    return str(self.client_address[0])

  def log_message(self, format, *args):
    logger.info(self.address_string() + " " + format % args)

  def do_GET(self):
    url = urlparse.urlparse(self.path)
    params = urlparse.parse_qs(url.query)
    path = url.path
    if path == "/favicon.ico":
      return

    nodeid = self.path.strip("/")
    # throws ValueError, but we can't seem to catch it??!
    # keeps on serving tho, oh well.
    nodeid = int(nodeid)
    
    if nodeid not in queues:
      self.send_response(404)
      self.send_header('Content-type', 'text/plain')
      self.end_headers()
      self.wfile.write("nodeid " + str(nodeid) + " not found.\n")
      return

    self.send_response(200)
    self.send_header('Content-type', 'text/plain')
    self.end_headers()

    count = 0
    out = []
    try:
      while True:
        data = queues[nodeid][0].get(block=False)
        if len(data) != len(out):
          out = data
        else:
          for i,d in enumerate(data):
            out[i] = out[i] + d
        count += 1
    except Queue.Empty:
      for i,d in enumerate(out):
        out[i] = out[i] / count

      labels = queues[nodeid][1]
      for i,d in enumerate(out):
        out[i] = labels[i] + ':' + str(d)
    if len(out) == 0:
      ret = []
      for l in labels:
        ret.append("U:" + l)
      self.wfile.write(" ".join(ret) + "\n")
    else:
      self.wfile.write(" ".join(out) + "\n")


if __name__ == "__main__":
  port = "/dev/ttyAMA0"
  queues = {
        10: (Queue.Queue(), ('CT1', 'CT2', 'CT3', 'Vcc')),
  }

  d = daemon.DaemonContext(pidfile=PidFile("/var/run/rfm12pipyd.pid"))
  d.open()

  logger = logging.root
  logger.setLevel(logging.DEBUG)
  syslog = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_DAEMON)
  formatter = logging.Formatter('RFM12Pi: %(levelname)s %(message)s')
  syslog.setFormatter(formatter)
  logger.addHandler(syslog)

  logger.info("RFM12Pi python thing starting up.")

  rpi = RFM12PIRx(port, queues)
  rpi.start()

  httpd = BaseHTTPServer.HTTPServer(("", 12345), Handler)
  httpd.serve_forever()
