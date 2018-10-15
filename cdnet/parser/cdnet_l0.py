#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>
#

from .cdnet_def import *


def to_frame(src, dst, dat, allow_share=True):
    src_addr = list(map(lambda x: x and int(x, 16) or 0, src[0].split(':')))
    dst_addr = list(map(lambda x: x and int(x, 16) or 0, dst[0].split(':')))
    src_port = src[1]
    dst_port = dst[1]
    assert dst_addr[0] == 0x00
    assert (src_port == CDNET_DEF_PORT and dst_port <= 63) or \
            dst_port == CDNET_DEF_PORT
    
    if src_port == CDNET_DEF_PORT:  # out request, backup dst port if need at outside
        payload = bytes([dst_port]) + dat
    else:                           # out reply
        if allow_share and len(dat) >= 1 and (dat[0] & L0_SHARE_MASK) == L0_SHARE_LEFT:
            # share first byte
            payload = bytes([(dat[0] & ~L0_SHARE_MASK) | HDR_L0_REPLY | HDR_L0_SHARE]) + dat[1:]
        else:
            payload = bytes([HDR_L0_REPLY]) + data
    
    frame = bytes([src_addr[2]]) + bytes([dst_addr[2]]) + bytes([len(payload)]) + payload
    assert len(frame) <= 256
    return frame


def from_frame(frame, local_net=0, last_port=None):
    hdr = frame[3]
    assert not (hdr & 0x80)
    
    src_mac = frame[0]
    dst_mac = frame[1]
    remains = frame[3:]
    assert len(remains) == frame[2]
    
    if hdr & HDR_L0_REPLY:  # in reply
        assert last_port != None
        src_port = last_port
        dst_port = CDNET_DEF_PORT
        if hdr & HDR_L0_SHARE:
            dat = bytes([(remains[0] & 0x1f) | L0_SHARE_LEFT]) + remains[1:]
        else:
            dat = remains[1:]
    else:                   # in request
        src_port = CDNET_DEF_PORT
        dst_port = hdr
        dat = remains[1:]
    
    src = '00:{:02x}:{:02x}'.format(local_net, src_mac)
    dst = '00:{:02x}:{:02x}'.format(local_net, dst_mac)
    return (src, src_port), (dst, dst_port), dat

