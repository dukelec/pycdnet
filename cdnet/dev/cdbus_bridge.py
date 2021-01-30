#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>

import threading
import queue
from ..utils.log import *
from ..dev.cdbus_serial import CDBusSerial


class CDBusBridge(threading.Thread):
    def __init__(self, port, baud=115200, timeout=0.5, name='cdnet.dev.bridge'):
        
        self.rx_queue = queue.Queue()
        self.rx_queue_55 = queue.Queue()
        self.logger = logging.getLogger(name)
        
        self.timeout = timeout
        self.dev = CDBusSerial(port, baud=baud, timeout=timeout, remote_filter=[0x55, 0x56])

        threading.Thread.__init__(self)
        self.daemon = True
        self.alive = True
        self.start()
        
        self.logger.debug('read info ...')
        self.dev.send(b'\xaa\x55\x03' + b'\x80\x01' + b'\x00')
        try:
            dat = self.rx_queue_55.get(timeout=timeout)
            self.logger.debug(f'info: {dat[6:]}')
        except queue.Empty:
            self.logger.debug('info: no response')
    
    @property
    def online(self):
        return self.dev._online
    
    @property
    def portstr(self):
        return self.dev.com.portstr if self.dev.com else None
    
    def run(self):
        while self.alive:
            frame = self.dev.recv(self.timeout)
            if frame and frame[0] == 0x56:
                self.rx_queue.put(frame[3:5] + bytes([frame[2]-2]) + frame[5:])
            elif frame and frame[0] == 0x55:
                self.rx_queue_55.put(frame)
    
    def stop(self):
        self.alive = False
        self.dev.stop()
        self.join()
    
    def send(self, frame): # add [aa 56]
        assert len(frame) == frame[2] + 3 and len(frame) <= 253
        return self.dev.send(b'\xaa\x56' + bytes([frame[2]+2]) + frame[0:2] + frame[3:])
    
    def recv(self, timeout=None):
        try:
            return self.rx_queue.get(timeout=timeout)
        except queue.Empty:
            return None

