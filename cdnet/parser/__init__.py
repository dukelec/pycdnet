#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>
#

# CDNET address format:
 #
 #              local link     unique local    multicast
 # level0:       00:NN:MM
 # level1:       80:NN:MM        a0:NN:MM       f0:MH:ML
 #  `-with seq:  88:NN:MM        a8:NN:MM       f8:MH:ML
 # level2:       c0:NN:MM
 #  `-with seq:  c8:NN:MM
 #
 # Notes:
 #   NN: net_id, MM: mac_addr, MH+ML: multicast_id

from .cdnet_def import *
from . import cdnet_l0
from . import cdnet_l1
from . import cdnet_l2
