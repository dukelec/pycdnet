#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>
#

from .cdnet_def import *


def to_frame(pkt, intf):
    assert pkt.level == CDNET_L0
    assert (pkt.src_port == CDNET_DEF_PORT and pkt.dst_port <= 63) or \
            pkt.dst_port == CDNET_DEF_PORT
    
    if pkt.src_port == CDNET_DEF_PORT:  # out request
        intf.l0_last_port = pkt.dst_port
        payload = bytes([pkt.dst_port]) + pkt.data
    else:                               # out reply
        if pkt.len >= 1 and pkt.dat[0] <= 31:
            # share first byte
            payload = bytes([pkt.dat[0] | HDR_L0_REPLY | HDR_L0_SHARE]) + pkt.dat[1:]
        else:
            payload = bytes([HDR_L0_REPLY]) + pkt.data
    
    frame = bytes([pkt.src_mac]) + bytes([pkt.dst_mac]) + bytes([len(payload)]) + payload
    assert len(frame) <= 256
    return frame


def from_frame(frame, intf):
    hdr = frame[3]
    assert not (hdr & 0x80)
    
    pkt = CDNetPacket(CDNET_L0)
    
    pkt.src_mac = frame[0]
    pkt.dst_mac = frame[1]
    remains = frame[3:]
    assert len(remains) == frame[2]
    
    if hdr & HDR_L0_REPLY:  # in reply
        assert l0_last_port != None
        pkt.src_port = intf.l0_last_port
        pkt.dst_port = CDNET_DEF_PORT
        if hdr & HDR_L0_SHARE:
            pkt.dat = bytes([remains[0] & 0x1f]) + remains[1:]
        else:
            pkt.dat = remains[1:]
    else:                   # in request
        pkt.src_port = CDNET_DEF_PORT
        pkt.dst_port = hdr
        pkt.dat = remains[1:]
    
    return pkt

