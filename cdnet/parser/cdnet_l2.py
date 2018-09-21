#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>
#

from .cdnet_def import *


def to_frame(src, dst, dat, max_size=253, seq_val=None, pos=0):
    src_addr = list(map(lambda x: x and int(x, 16) or 0, src[0].split(':')))
    dst_addr = list(map(lambda x: x and int(x, 16) or 0, dst[0].split(':')))
    assert dst_addr[0] == 0xc0 or dst_addr[0] == 0xc8
    user_flag = dst_addr[0] & 7
    seq = bool(dst_addr[0] & 8)
    payload_max = seq and max_size-1 or max_size
    
    if len(dat[pos:]) <= payload_max:
        frag = pos and CDNET_FRAG_LAST or CDNET_FRAG_NONE
    else:
        frag = pos and CDNET_FRAG_MORE or CDNET_FRAG_FIRST
    
    hdr = HDR_L1_L2 | HDR_L2 | user_flag
    payload = b''
    if seq:
        hdr |= HDR_L1_L2_SEQ
        payload += bytes([seq_val])
    if frag:
        assert seq
        hdr |= frag << 4
    
    body = dat[pos:payload_max]
    payload += body
    frame = bytes([src_addr[2]]) + bytes([dst_addr[2]]) + bytes([len(payload)+1]) + bytes([hdr]) + payload
    assert len(frame) <= 256
    return frame, len(body)


def from_frame(frame, local_net=0):
    hdr = frame[3]
    assert (hdr & 0xc0) == 0xc0
    seq = bool(hdr & HDR_L1_L2_SEQ)
    seq_val = None
    user_flag = hdr & 7
    
    src_addr = ((seq and 0xc8 or 0xc0) | user_flag, local_net, frame[0])
    dst_addr = ((seq and 0xc8 or 0xc0) | user_flag, local_net, frame[1])
    remains = frame[3:]
    assert len(remains) == frame[2]
    remains = remains[1:] # skip hdr
    
    if hdr & 0x30:
        assert seq
        frag = (hdr >> 4) & 3
    else:
        frag = CDNET_FRAG_NONE
    
    if seq:
        seq_val = remains[0]
        remains = remains[1:]
    
    dat = remains
    src = ':'.join('%02x' % x for x in src_addr)
    dst = ':'.join('%02x' % x for x in dst_addr)
    return (src, None), (dst, None), dat, seq_val, frag

