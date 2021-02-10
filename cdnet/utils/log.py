#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>


import logging

logging.VERBOSE = 5

def logger_init(level=logging.INFO):
    logging.basicConfig(format='%(asctime)s.%(msecs)03d %(name)s: %(levelname)s: %(message)s', datefmt='%H:%M:%S', level=level)
    logging.addLevelName(logging.VERBOSE, 'VERBOSE')

