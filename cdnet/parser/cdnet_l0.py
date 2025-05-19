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
    assert (src_port & 0xff80) == 0
    assert (dst_port & 0xff80) == 0

    payload = bytes([src_port])
    payload += bytes([dst_port])
    return payload + dat


def to_frame(src, dst, dat):
    src_addr = list(map(lambda x: x and int(x, 16) or 0, src[0].split(':')))
    dst_addr = list(map(lambda x: x and int(x, 16) or 0, dst[0].split(':')))
    assert dst_addr[0] == 0x00
    payload = to_payload(src, dst, dat)
    frame = bytes([src_addr[2], dst_addr[2], len(payload)]) + payload
    return frame



def from_payload(payload, src_mac, dst_mac, local_net=0):
    assert (payload[0] & 0x80) == 0
    assert (payload[1] & 0x80) == 0

    src_port = payload[0]
    dst_port = payload[1]
    dat = payload[2:] # skip hdr

    src = '00:{:02x}:{:02x}'.format(local_net, src_mac)
    dst = '00:{:02x}:{:02x}'.format(local_net, dst_mac)
    return (src, src_port), (dst, dst_port), dat


def from_frame(frame, local_net=0):
    src_mac = frame[0]
    dst_mac = frame[1]
    assert len(frame) == frame[2] + 3
    return from_payload(frame[3:], src_mac, dst_mac, local_net)


