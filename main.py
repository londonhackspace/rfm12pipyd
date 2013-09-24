#!/usr/bin/env python
import serial, threading, Queue, time
import BaseHTTPServer, urlparse, urllib

class RFM12PIRx(threading.Thread):
  def __init__(self, port, queue):
    super(RFM12PIRx, self).__init__()
    self.s = serial.Serial(port, 9600)
    self.q = queue
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
          print out
          self.q.put(out)
      else:
        if ord(data) != 1:
          d = d + data

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
  def address_string(self):
    return str(self.client_address[0])
    
  def do_GET(self):
    print self.path
    url = urlparse.urlparse(self.path)
    params = urlparse.parse_qs(url.query)
    path = url.path
    if path == "favicon.ico":
      return
    self.send_response(200)
    self.send_header('Content-type', 'text/plain')
    self.end_headers()
    count = 0
    out = []
    try:
      while True:
        data = queue.get(block=False)
        if len(data) != len(out):
          out = data
        else:
          for i,d in enumerate(data):
            out[i] = out[i] + d
        count += 1
    except Queue.Empty:
      print "done all"
      for i,d in enumerate(out):
        out[i] = out[i] / count

      print out, count
      labels = ('CT1', 'CT2', 'CT3', 'Vcc')
      for i,d in enumerate(out):
        out[i] = labels[i] + ':' + str(d)
    if len(out) == 0:
      self.wfile.write("NaN\n")
    else:
      self.wfile.write(" ".join(out) + "\n")
     
if __name__ == "__main__":
  queue = Queue.Queue()
  port = "/dev/ttyAMA0"
  rpi = RFM12PIRx(port, queue)
  rpi.start()

  httpd = BaseHTTPServer.HTTPServer(("", 12345), Handler)
  httpd.serve_forever()

  