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
L0_SHARE_MASK = 0xe0
L0_SHARE_LEFT = 0x80

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

