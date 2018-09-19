#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>
#

import struct as _struct
from .cdnet_def import *


def _get_port_size(val):
    if val == 0x00: return (0, 1)
    if val == 0x01: return (0, 2)
    if val == 0x02: return (1, 0)
    if val == 0x03: return (2, 0)
    if val == 0x04: return (1, 1)
    if val == 0x05: return (1, 2)
    if val == 0x06: return (2, 1)
    if val == 0x07: return (2, 2)
    raise ValueError("cdnet port field error")

def _cal_port_val(src, dst):
    if src == CDNET_DEF_PORT:
        src_size = 0
    elif src <= 0xff:
        src_size = 1
    else:
        src_size = 2
    
    if dst == CDNET_DEF_PORT:
        dst_size = 0
    elif dst <= 0xff:
        dst_size = 1
    else:
        dst_size = 2
    
    if (src_size, dst_size) == (0, 1): return (0x00, src_size, dst_size)
    if (src_size, dst_size) == (0, 2): return (0x01, src_size, dst_size)
    if (src_size, dst_size) == (1, 0): return (0x02, src_size, dst_size)
    if (src_size, dst_size) == (2, 0): return (0x03, src_size, dst_size)
    if (src_size, dst_size) == (1, 1): return (0x04, src_size, dst_size)
    if (src_size, dst_size) == (1, 2): return (0x05, src_size, dst_size)
    if (src_size, dst_size) == (2, 1): return (0x06, src_size, dst_size)
    if (src_size, dst_size) == (2, 2): return (0x07, src_size, dst_size)


def to_frame(pkt, _=None):
    assert pkt.level == CDNET_L1
    
    hdr = HDR_L1_L2 | (pkt.multi << 4)
    payload = b''
    
    if pkt.multi == CDNET_MULTI_CAST:
        payload += pkt.multicast_id.to_bytes(2, 'little')
    elif pkt.multi == CDNET_MULTI_NET:
        payload += bytes([pkt.src_addr.net])
        payload += bytes([pkt.src_addr.mac])
        payload += bytes([pkt.dst_addr.net])
        payload += bytes([pkt.dst_addr.mac])
    elif pkt.multi == CDNET_MULTI_CAST_NET:
        payload += bytes([pkt.src_addr.net])
        payload += bytes([pkt.src_addr.mac])
        payload += pkt.multicast_id.to_bytes(2, 'little')
    
    if pkt.seq:
        hdr |= HDR_L1_L2_SEQ
        payload += bytes([pkt._seq_num | (pkt._req_ack << 7)])
    
    print("{} {}".format(pkt.src_port, pkt.dst_port))
    port_size_val, src_port_size, dst_port_size = _cal_port_val(pkt.src_port, pkt.dst_port)
    hdr |= port_size_val
    
    if src_port_size == 1:
        payload += bytes([pkt.src_port])
    elif src_port_size == 2:
        payload += pkt.src_port.to_bytes(2, 'little')
    if dst_port_size == 1:
        payload += bytes([pkt.dst_port])
    elif dst_port_size == 2:
        payload += pkt.dst_port.to_bytes(2, 'little')
    
    payload += pkt.dat
    frame = bytes([pkt.src_mac]) + bytes([pkt.dst_mac]) + bytes([len(payload)+1]) + bytes([hdr]) + payload
    assert len(frame) <= 256
    return frame


def from_frame(frame, _=None):
    hdr = frame[3]
    assert (hdr & 0xc0) == 0x80
    
    pkt = CDNetPacket(CDNET_L1)
    
    pkt.src_mac = frame[0]
    pkt.dst_mac = frame[1]
    remains = frame[3:]
    assert len(remains) == frame[2]
    
    remains = remains[1:] # skip hdr
    
    pkt.seq = bool(hdr & HDR_L1_L2_SEQ)
    pkt.multi = (hdr >> 4) & 3
    
    if pkt.multi == CDNET_MULTI_CAST:
        pkt.multicast_id = _struct.unpack("<H", remains[:2])[0]
        remains = remains[2:]
    elif pkt.multi == CDNET_MULTI_NET:
        pkt.src_addr.net = remains[0]
        pkt.src_addr.mac = remains[1]
        pkt.dst_addr.net = remains[2]
        pkt.dst_addr.mac = remains[3]
        remains = remains[4:]
    elif pkt.multi == CDNET_MULTI_CAST_NET:
        pkt.src_addr.net = remains[0]
        pkt.src_addr.mac = remains[1]
        pkt.multicast_id = _struct.unpack("<H", remains[2:4])[0]
        remains = remains[4:]
    
    if pkt.seq:
        pkt._seq_num = remains[0] & 0x7f
        pkt._req_ack = bool(remains[0] & 0x80)
        remains = remains[1:]
    
    src_port_size, dst_port_size = _get_port_size(hdr & 0x07)
    
    if src_port_size == 0:
        pkt.src_port = CDNET_DEF_PORT
    elif src_port_size == 1:
        pkt.src_port = remains[0]
        remains = remains[1:]
    elif src_port_size == 2:
        pkt.src_port = _struct.unpack("<H", remains[:2])[0]
        remains = remains[2:]
    if dst_port_size == 0:
        pkt.dst_port = CDNET_DEF_PORT
    elif dst_port_size == 1:
        pkt.dst_port = remains[0]
        remains = remains[1:]
    elif dst_port_size == 2:
        pkt.dst_port = _struct.unpack("<H", remains[:2])[0]
        remains = remains[2:]
    
    pkt.dat = remains
    return pkt

