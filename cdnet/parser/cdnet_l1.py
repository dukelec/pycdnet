#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>
#

import struct as _struct
from .cdnet_def import *


def to_payload(src, dst, dat):
    src_addr = list(map(lambda x: x and int(x, 16) or 0, src[0].split(':')))
    dst_addr = list(map(lambda x: x and int(x, 16) or 0, dst[0].split(':')))
    src_port = src[1]
    dst_port = dst[1]

    assert src_addr[0] == 0x80 or src_addr[0] == 0xa0
    assert dst_addr[0] == 0x80 or dst_addr[0] == 0xa0 or dst_addr[0] == 0xf0

    multi = CDN_MULTI_NONE
    if src_addr[0] == 0xa0:
        multi |= CDN_MULTI_NET
    if dst_addr[0] == 0xf0:
        multi |= CDN_MULTI_CAST

    hdr = 0x80 | (multi << 4)
    payload = b''

    if multi & CDN_MULTI_NET:
        payload += bytes([src_addr[1]])
        payload += bytes([src_addr[2]])
    if multi != CDN_MULTI_NONE:
        payload += bytes([dst_addr[1]])
        payload += bytes([dst_addr[2]])

    payload += bytes([src_port & 0xff])
    if src_port & 0xff00:
        payload += bytes([src_port >> 8])
        hdr |= 2
    payload += bytes([dst_port & 0xff])
    if dst_port & 0xff00:
        payload += bytes([dst_port >> 8])
        hdr |= 1

    payload = bytes([hdr]) + payload + dat
    assert len(payload) <= 253
    return payload


def to_frame(src, dst, dat, src_mac, dst_mac):
    payload = to_payload(src, dst, dat)
    frame = bytes([src_mac, dst_mac, len(payload)]) + payload
    return frame



def from_payload(payload, src_mac, dst_mac, local_net=0):
    hdr = payload[0]
    assert (hdr & 0xc8) == 0x80

    remains = payload[1:] # skip hdr
    multi = (hdr >> 4) & 3

    if multi & CDN_MULTI_NET:
        src_addr = (0xa0,) + _struct.unpack("<BB", remains[:2])
        remains = remains[2:]
    else:
        src_addr = (0x80, local_net, src_mac)

    if multi != CDN_MULTI_NONE:
        dst_addr = (multi & CDN_MULTI_CAST) and (0xf0,) or (0xa0,)
        dst_addr += _struct.unpack("<BB", remains[:2])
        remains = remains[2:]
    else:
        dst_addr = (0x80, local_net, dst_mac)

    if hdr & 2:
        src_port = _struct.unpack("<H", remains[:2])[0]
        remains = remains[2:]
    else:
        src_port = _struct.unpack("<B", remains[:1])[0]
        remains = remains[1:]

    if hdr & 1:
        dst_port = _struct.unpack("<H", remains[:2])[0]
        remains = remains[2:]
    else:
        dst_port = _struct.unpack("<B", remains[:1])[0]
        remains = remains[1:]

    dat = remains
    src = bytes(src_addr).hex(':')
    dst = bytes(dst_addr).hex(':')
    return (src, src_port), (dst, dst_port), dat


def from_frame(frame, local_net=0):
    src_mac = frame[0]
    dst_mac = frame[1]
    assert len(frame) == frame[2] + 3
    return from_payload(frame[3:], src_mac, dst_mac, local_net)

