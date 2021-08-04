#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>


import logging
from serial.tools import list_ports
from fnmatch import fnmatch


def dump_ports(name='cdnet.dump_ports'):
    logger = logging.getLogger(name)
    for p in get_ports():
        logger.info(p)

def get_ports():
    ports = []
    for d in list_ports.comports():
        ports.append(f'{d.device} - {d.product} | {d.hwid}')
    return ports

def get_port(port, unique=False):
    # port: dev path or filter string
    ports = get_ports()
    left = [p for p in ports if fnmatch(p, '*'+port+'*')]
    if len(left) == 0 or (unique and len(left) > 1):
        return None
    return left[0].split(' - ')[0]


if __name__ == "__main__":
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    dump_ports()

