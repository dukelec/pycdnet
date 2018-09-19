#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>


import logging

logging.VERBOSE = 5

def logger_init(level=logging.INFO):
    logging.basicConfig(format='%(name)s: %(levelname)s: %(message)s', level=level)
    logging.addLevelName(logging.VERBOSE, 'VERBOSE')

