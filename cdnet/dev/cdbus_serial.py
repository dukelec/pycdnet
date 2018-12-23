#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>

# pip3 install pycrc --user
from PyCRC.CRC16 import CRC16

import threading
import queue
import serial
from ..utils.select_serial_port import select_port
from ..utils.log import *


def modbus_crc(frame):
    return CRC16(modbus_flag=True).calculate(frame)

def to_hexstr(data):
    return ' '.join('%02x' % b for b in data)


class CDBusSerial(threading.Thread):
    def __init__(self, name='cdbus_serial',
                       dev_filters=None, dev_port=None, baud=115200, dev_timeout=0.5,
                       local_filter=[0xaa], remote_filter=[0x55]):
        
        self.rx_queue = queue.Queue()
        
        self.local_filter = local_filter
        self.remote_filter = remote_filter
        
        self.rx_bytes = b''
        self.logger = logging.getLogger(name)
        
        dev_port = select_port(logger=self.logger, dev_port=dev_port, filters=dev_filters)
        if not dev_port:
            raise Exception('device not exist')
        
        # TODO: add auto reconnection support
        self.com = serial.Serial(port=dev_port, baudrate=baud, timeout=dev_timeout)
        if not self.com.isOpen():
            raise Exception('serial open failed')
        threading.Thread.__init__(self)
        self.daemon = True
        self.alive = True
        self.start()
    
    def run(self):
        while self.alive:
            bchar = self.com.read()
            if len(bchar) == 0:
                if len(self.rx_bytes) != 0:
                    self.logger.warning('timeout drop: ' + to_hexstr(self.rx_bytes))
                    self.rx_bytes = b''
                continue
            
            rx_dat = bchar + self.com.read_all()
            #self.logger.log(logging.VERBOSE, '>>> ' + to_hexstr(in_dat))
            
            while len(rx_dat):
                if len(self.rx_bytes) == 0:
                    self.rx_bytes, rx_dat = rx_dat[:1], rx_dat[1:]
                    if self.rx_bytes[0] not in self.remote_filter:
                        self.logger.debug('byte0 filtered: %02x' % self.rx_bytes[0])
                        self.rx_bytes = b''
                        break
                if not len(rx_dat):
                    break
                
                if len(self.rx_bytes) == 1:
                    self.rx_bytes += rx_dat[:1]
                    rx_dat = rx_dat[1:]
                    if self.rx_bytes[1] not in self.local_filter:
                        self.logger.debug('byte1 filtered: %02x' % self.rx_bytes[1])
                        self.rx_bytes = b''
                        break
                if not len(rx_dat):
                    break
                
                if len(self.rx_bytes) == 2:
                    self.rx_bytes += rx_dat[:1]
                    rx_dat = rx_dat[1:]
                
                max_left = self.rx_bytes[2] + 5 - len(self.rx_bytes)
                self.rx_bytes += rx_dat[:max_left]
                rx_dat = rx_dat[max_left:]
                
                if len(self.rx_bytes) == self.rx_bytes[2] + 5:
                    if modbus_crc(self.rx_bytes) != 0:
                        self.logger.debug('crc error: ' + to_hexstr(self.rx_bytes))
                        self.rx_bytes = b''
                        break
                    else:
                        self.logger.log(logging.VERBOSE, '-> ' + to_hexstr(self.rx_bytes[:-2]))
                        self.rx_queue.put(self.rx_bytes[:-2])
                        self.rx_bytes = b''
            
            if len(rx_dat):
                self.logger.debug('drop left: ' + to_hexstr(rx_dat))
        
        self.com.close()
    
    def stop(self):
        self.alive = False
        self.join()
    
    def send(self, frame):
        self.logger.log(logging.VERBOSE, '<- ' + to_hexstr(frame))
        assert len(frame) == frame[2] + 3
        frame += modbus_crc(frame).to_bytes(2, byteorder='little')
        self.com.write(frame)
    
    def recv(self, timeout=None):
        return self.rx_queue.get(timeout=timeout)

