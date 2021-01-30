#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>

# pip3 install pythoncrc
from PyCRC.CRC16 import CRC16

import threading
import queue
import serial
from time import sleep
from ..utils.serial_get_port import *
from ..utils.log import *


def modbus_crc(frame):
    return CRC16(modbus_flag=True).calculate(frame)


class CDBusSerial(threading.Thread):
    def __init__(self, port, baud=115200, timeout=0.5, echo=False,
                       local_filter=[0xaa], remote_filter=[0x55], name='cdnet.dev.serial'):
        '''
        port: dev path or filter string
        '''
        
        self.rx_queue = queue.Queue()
        
        self.port = port
        self.baud = baud
        self.timeout = timeout
        
        self.local_filter = local_filter
        self.remote_filter = remote_filter
        self.echo = echo
        self.echo_dat = None
        
        self.rx_bytes = b''
        self.logger = logging.getLogger(name)
        
        dev_port = get_port(port)
        if not dev_port:
            self.logger.error(f'device not exist, available devices:')
            dump_ports(name)
            raise Exception('device not exist')
        self.com = serial.Serial(port=dev_port, baudrate=baud, timeout=timeout)
        if not self.com.isOpen():
            raise Exception('serial open failed')
        
        threading.Thread.__init__(self)
        self.daemon = True
        self._online = True
        self.alive = True
        self.start()
    
    @property
    def online(self):
        return self._online
    
    @property
    def portstr(self):
        return self.com.portstr if self.com else None
    
    def run(self):
        while self.alive:
            while not self._online:
                if not self.alive:
                    self.com.close()
                    return
                dev_port = get_port(self.port)
                if dev_port:
                    self.com = serial.Serial(port=dev_port, baudrate=self.baud, timeout=self.timeout)
                    if self.com.isOpen():
                        self._online = True
                        self.logger.info(f're-connected: {self.port} ({dev_port})')
                        break
                self.logger.warn(f'retry connect: {self.port} ...')
                sleep(1)
            
            try:
                bchar = self.com.read()
                if len(bchar) == 0:
                    if len(self.rx_bytes) != 0:
                        self.logger.warning('timeout drop: ' + self.rx_bytes.hex(' '))
                        self.rx_bytes = b''
                    continue
                
                rx_dat = bchar + self.com.read_all()
                #self.logger.log(logging.VERBOSE, '>>> ' + in_dat.hex(' '))
                
                if self.echo_dat:
                    if (rx_dat.find(self.echo_dat) == 0):
                        rx_dat = rx_dat[len(self.echo_dat):]
                    self.echo_dat = None
                
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
                            self.logger.debug('crc error: ' + self.rx_bytes.hex(' '))
                            self.rx_bytes = b''
                            break
                        else:
                            self.logger.log(logging.VERBOSE, '-> ' + self.rx_bytes[:-2].hex(' '))
                            self.rx_queue.put(self.rx_bytes[:-2])
                            self.rx_bytes = b''
                
                if len(rx_dat):
                    self.logger.debug('drop left: ' + rx_dat.hex(' '))
            
            except serial.serialutil.SerialException as err:
                self._online = False
                self.logger.warn(f'{err}')
                self.logger.warn(f're-open: {self.port} ...')
                self.com.close()
                self.echo_dat = None
                self.rx_bytes = b''
                sleep(1)
        
        self.com.close()
    
    def stop(self):
        self.alive = False
        self.com.close()
        self.join()
    
    def send(self, frame):
        self.logger.log(logging.VERBOSE, '<- ' + frame.hex(' ')) # python >= v3.8
        assert len(frame) == frame[2] + 3
        frame += modbus_crc(frame).to_bytes(2, byteorder='little')
        if self.echo:
            self.echo_dat = frame
        try:
            self.com.write(frame)
            return None
        except serial.serialutil.SerialException as err:
            self.logger.warn(f'send: {err}')
            return err
    
    def recv(self, timeout=None):
        try:
            return self.rx_queue.get(timeout=timeout)
        except queue.Empty:
            return None

