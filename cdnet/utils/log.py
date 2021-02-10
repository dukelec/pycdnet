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
    logging.basicConfig(format='%(created).3f %(name)s: %(levelname)s: %(message)s', level=level)
    logging.addLevelName(logging.VERBOSE, 'VERBOSE')

