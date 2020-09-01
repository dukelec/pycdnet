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
    
    if dst == CDNET_DEF_PORT and src != CDNET_DEF_PORT:
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


def to_frame(src, dst, dat, src_mac, seq_val=None):
    src_addr = list(map(lambda x: x and int(x, 16) or 0, src[0].split(':')))
    dst_addr = list(map(lambda x: x and int(x, 16) or 0, dst[0].split(':')))
    src_port = src[1]
    dst_port = dst[1]
    
    assert (dst_addr[0] & 0xc0) == 0x80 and (dst_addr[0] & 7) == 0
    
    multi = (dst_addr[0] >> 4) & 3
    
    hdr = HDR_L1_L2 | (multi << 4)
    payload = b''
    
    if multi == CDNET_MULTI_CAST:
        payload += dst_addr[1].to_bytes(2, 'little')
        assert src_addr[2] == src_mac
        dst_mac = dst_addr[1] & 0xff
    elif multi == CDNET_MULTI_NET:
        payload += bytes([src_addr[1]])
        payload += bytes([src_addr[2]])
        payload += bytes([dst_addr[1]])
        payload += bytes([dst_addr[2]])
        dst_mac = cdnet_get_router(dst) # TODO: implement this function
    elif multi == CDNET_MULTI_CAST_NET:
        payload += bytes([src_addr[1]])
        payload += bytes([src_addr[2]])
        payload += dst_addr[1].to_bytes(2, 'little')
        dst_mac = dst_addr[1] & 0xff # TODO: set to 255 if remote hw filter not enough
    else:
        assert src_addr[2] == src_mac
        dst_mac = dst_addr[2]
    
    if dst_addr[0] & 8:
        hdr |= HDR_L1_L2_SEQ
        payload += bytes([seq_val])
    
    port_size_val, src_port_size, dst_port_size = _cal_port_val(src_port, dst_port)
    hdr |= port_size_val
    
    if src_port_size == 1:
        payload += bytes([src_port])
    elif src_port_size == 2:
        payload += src_port.to_bytes(2, 'little')
    if dst_port_size == 1:
        payload += bytes([dst_port])
    elif dst_port_size == 2:
        payload += dst_port.to_bytes(2, 'little')
    
    payload += dat
    frame = bytes([src_mac]) + bytes([dst_mac]) + bytes([len(payload)+1]) + bytes([hdr]) + payload
    assert len(frame) <= 256
    return frame


def from_frame(frame, local_net=0):
    hdr = frame[3]
    assert (hdr & 0xc0) == 0x80
    
    src_mac = frame[0]
    dst_mac = frame[1]
    remains = frame[3:]
    assert len(remains) == frame[2]
    
    remains = remains[1:] # skip hdr
    
    seq = bool(hdr & HDR_L1_L2_SEQ)
    seq_val = None
    multi = (hdr >> 4) & 3
    
    if multi == CDNET_MULTI_CAST:
        src_addr = (seq and 0x88 or 0x80, local_net, src_mac)
        m_id = _struct.unpack("<H", remains[:2])[0]
        dst_addr = (seq and 0x98 or 0x90, m_id)
        remains = remains[2:]
    elif multi == CDNET_MULTI_NET:
        src_addr = (seq and 0xa8 or 0xa0, remains[0], remains[1])
        dst_addr = (seq and 0xa8 or 0xa0, remains[2], remains[3])
        remains = remains[4:]
    elif multi == CDNET_MULTI_CAST_NET:
        src_addr = (seq and 0xa8 or 0xa0, remains[0], remains[1])
        m_id = _struct.unpack("<H", remains[2:4])[0]
        dst_addr = (seq and 0xb8 or 0xb0, m_id)
        remains = remains[4:]
    else:
        src_addr = (seq and 0x88 or 0x80, local_net, src_mac)
        dst_addr = (seq and 0x88 or 0x80, local_net, dst_mac)
    
    if seq:
        seq_val = remains[0]
        remains = remains[1:]
    
    src_port_size, dst_port_size = _get_port_size(hdr & 0x07)
    
    if src_port_size == 0:
        src_port = CDNET_DEF_PORT
    elif src_port_size == 1:
        src_port = remains[0]
        remains = remains[1:]
    elif src_port_size == 2:
        src_port = _struct.unpack("<H", remains[:2])[0]
        remains = remains[2:]
    if dst_port_size == 0:
        dst_port = CDNET_DEF_PORT
    elif dst_port_size == 1:
        dst_port = remains[0]
        remains = remains[1:]
    elif dst_port_size == 2:
        dst_port = _struct.unpack("<H", remains[:2])[0]
        remains = remains[2:]
    
    dat = remains
    src = bytes(src_addr).hex(':')
    dst = bytes(dst_addr).hex(':')
    return (src, src_port), (dst, dst_port), dat, seq_val

