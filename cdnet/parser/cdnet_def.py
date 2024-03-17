#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>
#

import os as _os

CDN_DEF_PORT = int(_os.environ['CDN_DEF_PORT'], 0) if 'CDN_DEF_PORT' in _os.environ else 0xcdcd
CDN0_SHARE_LEFT = 0x80

CDN_MULTI_NONE = 0
CDN_MULTI_CAST = 1
CDN_MULTI_NET = 2
CDN_MULTI_CAST_NET = 3

CDN_HDR_L0_REPLY = (1 << 6)

