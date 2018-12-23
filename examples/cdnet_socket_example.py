#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>


import sys, os
from time import sleep

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from cdnet.utils.log import *
from cdnet.dev.cdbus_serial import CDBusSerial
from cdnet.dispatch import *

logger_init(logging.VERBOSE)
#logger_init(logging.DEBUG)
#logger_init(logging.INFO)


dev = CDBusSerial(dev_port='/dev/ttyUSB0')
CDNetIntf(dev, net=0, mac=0xaa)
sock = CDNetSocket(('', 0xcdcd))

sock.sendto(b'', ('80:00:55', 1)) # level1, target: mac 55, port 1

print('wait recv')
rx = sock.recvfrom()

print('recv:', rx)

