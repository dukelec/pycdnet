#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>


import sys, os
from time import sleep

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from cdnet.utils.log import *
from cdnet.dev.cdbus_serial import CDBusSerial
from cdnet.dispatch import *

logger_init(logging.VERBOSE)
#logger_init(logging.DEBUG)
#logger_init(logging.INFO)


dev = CDBusSerial('/dev/ttyACM0', 115200) # dev path or filter string
CDNetIntf(dev, net=0, mac=0x00)
sock = CDNetSocket(('', 0x40)) # port 0x40

sock.sendto(b'', ('00:00:ff', 1)) # level0, target: broadcast, port 1

print('wait recv')
rx = sock.recvfrom()

print('recv:', rx)

