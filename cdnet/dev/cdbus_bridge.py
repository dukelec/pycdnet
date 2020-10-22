#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>

import threading
import queue
from ..utils.log import *
from ..dev.cdbus_serial import CDBusSerial
from ..dispatch import *


class DummySerial():
    def __init__(self, dev):
        self.dev = dev
        self.rx_queue = queue.Queue()
    
    def send(self, frame): # send by control channel
        assert frame[1] == 0x55
        self.dev.send(frame)
    
    def recv(self, timeout=None): # recv by control channel
        return self.rx_queue.get(timeout=timeout)


class CDBusBridge(threading.Thread):
    def __init__(self, name='cdbus_bridge',
                       dev_filters=None, dev_port=None, baud=115200, dev_timeout=0.5,
                       filter_=0x00):
        
        self.rx_queue = queue.Queue()
        self.logger = logging.getLogger(name)
        
        self.dev = CDBusSerial(dev_filters=dev_filters, dev_port=dev_port,
                               baud=baud, dev_timeout=dev_timeout, remote_filter=[0x55, 0x56])
        self.dummy = DummySerial(self.dev)
        
        # namespace and socket for control channel
        self.ns = CDNetNS()
        CDNetIntf(self.dummy, mac=0xaa, ns=self.ns)
        self.sock = CDNetSocket(('', 0xcdcd), ns=self.ns)

        threading.Thread.__init__(self)
        self.daemon = True
        self.alive = True
        self.start()
        
        self.logger.debug('read info ...')
        self.sock.sendto(b'\x00', ('80:00:55', 1))
        dat = self.sock.recvfrom()[0]
        self.logger.debug('info: {}'.format(dat[1:]))
        
        '''
        self.sock.sendto(b'\x68\x00' + bytes([filter_]), ('80:00:55', 3))
        dat = self.sock.recvfrom()[0]
        if len(dat) == 1 and dat[0] == 0x80:
            self.logger.debug('set filter to %d successed' % filter_)
        else:
            self.logger.error('set filter to %d error' % filter_)
        '''
    
    def run(self):
        while self.alive:
            frame = self.dev.recv()
            if frame[0] == 0x56:
                self.rx_queue.put(frame[3:5] + bytes([frame[2]-2]) + frame[5:])
            else:
                self.dummy.rx_queue.put(frame)
    
    def stop(self):
        # TODO: break blocking read
        self.alive = False
        self.ns.intfs[0].stop()
        self.join()
    
    def send(self, frame): # add [aa 56]
        assert len(frame) == frame[2] + 3 and len(frame) <= 253
        self.dev.send(b'\xaa\x56' + bytes([frame[2]+2]) + frame[0:2] + frame[3:])
    
    def recv(self, timeout=None):
        return self.rx_queue.get(timeout=timeout)

