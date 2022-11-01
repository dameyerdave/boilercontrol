#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, os, rrdtool, time
from datetime import datetime as dt

# function: read and parse sensor data file
def read_sensor(path):
  value = "U"
  try:
    f = open(path, "r")
    line = f.readline()
    if re.match(r"([0-9a-f]{2} ){9}: crc=[0-9a-f]{2} YES", line):
      line = f.readline()
      m = re.match(r"([0-9a-f]{2} ){9}t=([+-]?[0-9]+)", line)
      if m:
        value = str(float(m.group(2)) / 1000.0)
    f.close()
  except IOError as e:
    print(time.strftime("%x %X"), "Error reading", path, ": ", e)
  return value

# define pathes to 1-wire sensor data
pathes = (
  "/sys/bus/w1/devices/28-0621c1b4fce2/w1_slave",
  "/sys/bus/w1/devices/28-0621c1cdcdda/w1_slave",
  "/sys/bus/w1/devices/28-0921c1043e9c/w1_slave",
  "/sys/bus/w1/devices/28-0821c109a808/w1_slave",
  "/sys/bus/w1/devices/28-0621c1abece9/w1_slave",
  "/sys/bus/w1/devices/28-0821c0da11c5/w1_slave"
)

# read sensor data
data = 'N'
for path in pathes:
  data += ':'
  data += read_sensor(path)
  time.sleep(1)

print(f"{dt.now()} readTemperatures: {data}")

# insert data into round-robin-database
rrdtool.update(
  "%s/temperature.rrd" % (os.path.dirname(os.path.abspath(__file__))),
  data)


