#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>
#

import os as _os

CDNET_DEF_PORT = int(_os.environ['CDNET_DEF_PORT'], 0) if 'CDNET_DEF_PORT' in _os.environ else 0xcdcd

# ephemeral port start
CDNET_LOCAL_PORT = int(_os.environ['CDNET_LOCAL_PORT'], 0) if 'CDNET_LOCAL_PORT' in _os.environ else 32768


CDNET_L0 = 0
CDNET_L1 = 1
CDNET_L2 = 2

CDNET_MULTI_NONE = 0
CDNET_MULTI_CAST = 1
CDNET_MULTI_NET = 2
CDNET_MULTI_CAST_NET = 3

CDNET_FRAG_NONE = 0
CDNET_FRAG_FIRST = 1
CDNET_FRAG_MORE = 2
CDNET_FRAG_LAST = 3

HDR_L1_L2       = (1 << 7)
HDR_L2          = (1 << 6)

HDR_L0_REPLY    = (1 << 6)
HDR_L0_SHARE    = (1 << 5)

HDR_L1_L2_SEQ   = (1 << 3)


class CDNetAddr():
    def __init__(self, net = None, mac = None):
        self.net = net
        self.mac = mac
    def __repr__(self):
        return 'CDNetAddr: {}'.format(self.__dict__)


class CDNetPacket():
    def __init__(self, level = CDNET_L0, multi = CDNET_MULTI_NONE):
        self.level = level
        
        self.src_mac = None
        self.dst_mac = None
        
        if level != CDNET_L0:
            self.seq = False
            self._req_ack = False
            self._seq_num = None
            self._send_time = None
            
            self.multi = CDNET_MULTI_NONE
        
        if level == CDNET_L1:
            self.src_addr = CDNetAddr()
            self.dst_addr = CDNetAddr()
            self.multicast_id = None
        
        if level == CDNET_L2:
            self.frag = CDNET_FRAG_NONE
            self.l2_flag = 0
        
        self.src_port = None
        self.dst_port = None
        
        
        self.dat = b''
        
    def __repr__(self):
        return 'CDNetPacket: {}'.format(self.__dict__)


