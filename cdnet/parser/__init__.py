#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>
#

# CDNET address string format:
#
#              local link     unique local    local and cross net multicast
# level0:       00:NN:MM
# level1:       80:NN:MM        a0:NN:MM     90:M_ID     b0:M_ID
#  `-with seq:  88:NN:MM        a8:NN:MM     98:M_ID     b8:M_ID
# level2:       c0:NN:MM
#  `-with seq:  c8:NN:MM
#
# Notes:
#   NN: net_id, MM: mac_addr, M_ID: multicast_id (include scope)

from .cdnet_def import *
from . import cdnet_l0
from . import cdnet_l1
from . import cdnet_l2
