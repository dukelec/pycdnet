#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>
#

from .cdnet_def import *


def to_frame(pkt, _=None):
    assert pkt.level == CDNET_L2
    assert (pkt.l2_flag & ~7) == 0
    assert (pkt.frag & ~3) == 0
    
    hdr = HDR_L1_L2 | HDR_L2 | pkt.l2_flag
    payload = b''
    
    if pkt.frag:
        assert pkt.seq
        hdr |= pkt.frag << 4
    
    if pkt.seq:
        hdr |= HDR_L1_L2_SEQ
        payload += bytes([pkt._seq_num | (pkt._req_ack << 7)])
    
    payload += pkt.dat
    frame = bytes([pkt.src_mac]) + bytes([pkt.dst_mac]) + bytes([len(payload)+1]) + bytes([hdr]) + payload
    assert len(frame) <= 256
    return frame


def from_frame(frame, _=None):
    hdr = frame[3]
    assert (hdr & 0xc0) == 0xc0
    
    pkt = CDNetPacket(CDNET_L2)
    
    pkt.src_mac = frame[0]
    pkt.dst_mac = frame[1]
    remains = frame[3:]
    assert len(remains) == frame[2]
    
    remains = remains[1:] # skip hdr
    
    pkt.seq = bool(hdr & HDR_L1_L2_SEQ)
    pkt.l2_flag = hdr & 7
    
    if hdr & 0x30:
        assert pkt.seq
        pkt.frag = (hdr >> 4) & 3
    else:
        pkt.frag = CDNET_FRAG_NONE
    
    if pkt.seq:
        pkt._seq_num = remains[0] & 0x7f
        pkt._req_ack = bool(remains[0] & 0x80)
        remains = remains[1:]
    
    pkt.dat = remains
    return pkt

