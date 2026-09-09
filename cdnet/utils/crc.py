#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>


def gen_crc16_tab(poly=0xa001):
    tab = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ poly if c & 1 else c >> 1
        tab.append(c)
    return tab

CRC16_TAB = gen_crc16_tab()


def modbus_crc(dat, crc=0xffff):
    '''
    crc: initial value, pass the previous result to continue on the next chunk.
    Appending the result as 2 bytes little endian makes modbus_crc() of the
    whole frame return 0.
    '''
    tab = CRC16_TAB
    for b in dat:
        crc = (crc >> 8) ^ tab[(crc ^ b) & 0xff]
    return crc
