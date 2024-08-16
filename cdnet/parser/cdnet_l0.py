#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>
#

from .cdnet_def import *


def to_payload(src, dst, dat):
    src_port = src[1]
    dst_port = dst[1]
    assert (src_port == CDN_DEF_PORT and dst_port <= 63) or \
            dst_port == CDN_DEF_PORT

    if src_port == CDN_DEF_PORT:            # out request, backup dst port if need at outside
        payload = bytes([dst_port]) + dat
    else:                                   # out reply
        assert len(dat) >= 1
        assert (dat[0] & 0xc0) == CDN0_SHARE_LEFT
        # share first byte
        payload = bytes([(dat[0] & 0x3f) | CDN_HDR_L0_REPLY]) + dat[1:]

    assert len(payload) <= 253
    return payload


def to_frame(src, dst, dat):
    src_addr = list(map(lambda x: x and int(x, 16) or 0, src[0].split(':')))
    dst_addr = list(map(lambda x: x and int(x, 16) or 0, dst[0].split(':')))
    assert dst_addr[0] == 0x00
    payload = to_payload(src, dst, dat)
    frame = bytes([src_addr[2], dst_addr[2], len(payload)]) + payload
    return frame



def from_payload(payload, src_mac, dst_mac, local_net=0, last_port=None):
    hdr = payload[0]
    assert not (hdr & 0x80)

    remains = payload[1:] # skip hdr

    if hdr & CDN_HDR_L0_REPLY:  # in reply
        assert last_port != None
        src_port = last_port
        dst_port = CDN_DEF_PORT
        dat = bytes([(hdr & 0x3f) | CDN0_SHARE_LEFT]) + remains
    else:                       # in request
        src_port = CDN_DEF_PORT
        dst_port = hdr
        dat = remains

    src = '00:{:02x}:{:02x}'.format(local_net, src_mac)
    dst = '00:{:02x}:{:02x}'.format(local_net, dst_mac)
    return (src, src_port), (dst, dst_port), dat


def from_frame(frame, local_net=0, last_port=None):
    src_mac = frame[0]
    dst_mac = frame[1]
    assert len(frame) == frame[2] + 3
    return from_payload(frame[3:], src_mac, dst_mac, local_net, last_port)


