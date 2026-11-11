#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>

"""The port is served by a process of its own: a bus stream has no flow control,
if the port is not read for some tens of ms the bridge drops frames, and a thread
in a busy program cannot promise that, it has to win the GIL back after every read.
"""

import json
import os
import signal
import struct
import subprocess
import sys
import threading
import traceback
import queue
import serial
from time import sleep, time_ns, monotonic
from ..utils.serial_get_port import *
from ..utils.crc import *
from ..utils.log import *

TS_LEN = 8
HDR = struct.Struct('<BI') # kind, payload length
K_FRAME, K_STATE, K_LOG, K_BAUD, K_TX, K_TX_ERR = range(6)

PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHILD_BOOT = 'import sys; sys.path.insert(0, sys.argv[1]); from cdnet.dev.cdbus_serial import _child_main; _child_main()'


def _pack(kind, dat):
    return HDR.pack(kind, len(dat)) + dat


def _read_records(fd):
    buf = b''
    while True:
        dat = os.read(fd, 65536)
        if not dat:
            return
        buf += dat
        pos = 0
        while len(buf) - pos >= HDR.size:
            kind, n = HDR.unpack_from(buf, pos)
            end = pos + HDR.size + n
            if end > len(buf):
                break
            yield kind, buf[pos + HDR.size:end]
            pos = end
        buf = buf[pos:]


class CDBusSerial(threading.Thread):
    def __init__(self, port, baud=115200, timeout=0.05, echo=False,
                       local_filter=[], remote_filter=[], name='cdnet.dev.serial', on_tx=None):
        '''
        port: dev path or filter string
        timeout: serial read timeout, also the silence after which an
                 incomplete frame is dropped. Keep it above the usb-serial
                 chip forwarding latency (16 ms on ftdi by default), or a
                 valid frame split across usb packets would be dropped.
        on_tx: called from recv(), in order with the frames it returns:
               (ts_ns, frame, None) with the time of the write (crc stripped),
               then (ts_ns, None, err_text) if that write failed
        '''

        self.rx_queue = queue.Queue()
        self.port = port
        self.baud = baud
        self.on_tx = on_tx
        self.alive = True
        self.logger = logging.getLogger(name)
        self._online = False
        self._portstr = None
        self._ready = threading.Event()
        self._tx_lock = threading.Lock()

        # the level goes along so that nothing below it is even formatted over there
        args = [[port, baud, timeout, echo, local_filter, remote_filter, name], self.logger.getEffectiveLevel()]
        self.proc = subprocess.Popen([sys.executable, '-c', CHILD_BOOT, PKG_ROOT, json.dumps(args)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

        threading.Thread.__init__(self)
        self.daemon = True
        self.start()
        self._ready.wait() # the port has been tried, the first request must not outrun it

    @property
    def online(self):
        return self._online

    @property
    def portstr(self):
        return self._portstr

    def run(self):
        for kind, dat in _read_records(self.proc.stdout.fileno()):
            if kind == K_FRAME or (self.on_tx and kind in (K_TX, K_TX_ERR)):
                self.rx_queue.put((kind, int.from_bytes(dat[:TS_LEN], 'little'), dat[TS_LEN:]))
            elif kind == K_STATE:
                self._online, self._portstr = json.loads(dat)
                self._ready.set()
            elif kind == K_LOG:
                name, level, msg = json.loads(dat)
                logging.getLogger(name).log(level, msg) # filtered here, the level may have changed
        self._online = False
        self._ready.set()
        if self.alive:
            self.logger.error(f'serial process exited: {self.proc.wait()}')

    def _tx(self, kind, dat):
        try:
            with self._tx_lock:
                self.proc.stdin.write(_pack(kind, dat))
            return None
        except (OSError, ValueError) as err: # ValueError: after stop()
            self.logger.warning(f'send: {err}')
            return err

    def send(self, frame):
        assert len(frame) == frame[2] + 3
        err = self._tx(K_FRAME, frame) # offline too, the failure then goes through on_tx in order
        if not err and not self._online:
            err = serial.serialutil.PortNotOpenError()
        return err

    def set_baud(self, baud):
        self.baud = baud
        self._tx(K_BAUD, json.dumps(baud).encode())

    def recv(self, timeout=None, with_ts=False):
        """the next frame (crc stripped), None on timeout; with_ts: (ts_ns, frame), ts_ns when it was read in"""
        end = None if timeout is None else monotonic() + timeout
        while True:
            try:
                kind, ts, dat = self.rx_queue.get(timeout=None if end is None else max(end - monotonic(), 0))
            except queue.Empty:
                return None
            if kind == K_FRAME:
                return (ts, dat) if with_ts else dat
            if kind == K_TX:
                self.on_tx(ts, dat, None)
            else:
                self.on_tx(ts, None, dat.decode())

    def stop(self):
        self.alive = False
        with self._tx_lock:
            self.proc.stdin.close()
        self.join()
        self.proc.wait() # the port is free once this returns


class _SerialWorker(threading.Thread):
    def __init__(self, out_q, port, baud, timeout, echo, local_filter, remote_filter, name):
        self.out_q = out_q
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.com = None
        self._online = False

        self.local_filter = local_filter
        self.remote_filter = remote_filter
        self.echo = echo
        self.echo_dat = None

        self.rx_bytes = b''
        self.logger = logging.getLogger(name)

        dev_port = get_port(port)
        if not dev_port:
            dev_port = port # try hidden port
        try:
            self.com = serial.Serial(port=dev_port, baudrate=baud, timeout=timeout, exclusive=True)
            if self.com.isOpen():
                self._online = True
        except serial.serialutil.SerialException as err:
            self.logger.warning(f'connect {self.port} err: {err}')
        self._report()

        threading.Thread.__init__(self)
        self.daemon = True
        self.start()

    def _report(self):
        portstr = self.com.portstr if self.com else None
        self.out_q.put(_pack(K_STATE, json.dumps([self._online, portstr]).encode()))

    def run(self):
        try:
            self._loop()
        except Exception:
            traceback.print_exc()
            os._exit(1) # the parent's thread ends with us, that is how a dead port is seen

    def _loop(self):
        while True:
            while not self._online:
                dev_port = get_port(self.port)
                if dev_port:
                    try:
                        self.com = serial.Serial(port=dev_port, baudrate=self.baud, timeout=self.timeout, exclusive=True)
                        if self.com.isOpen():
                            self._online = True
                            self._report()
                            self.logger.info(f're-connected: {self.port} ({dev_port})')
                            break
                    except serial.serialutil.SerialException as err:
                        self.logger.warning(f'connect {self.port} err: {err}')
                self.logger.warning(f'retry connect: {self.port} ...')
                sleep(0.5)

            try:
                bchar = self.com.read()
                if len(bchar) == 0:
                    if len(self.rx_bytes) != 0:
                        self.logger.warning('timeout drop: ' + self.rx_bytes.hex(' '))
                        self.rx_bytes = b''
                    continue

                rx_ts = time_ns() # when the frames of this read came in, give or take the usb poll
                rx_dat = bchar + self.com.read_all()
                #self.logger.log(logging.VERBOSE, '>>> ' + in_dat.hex(' '))

                if self.echo_dat:
                    if (rx_dat.find(self.echo_dat) == 0):
                        rx_dat = rx_dat[len(self.echo_dat):]
                    self.echo_dat = None

                while len(rx_dat):
                    if len(self.rx_bytes) == 0:
                        self.rx_bytes, rx_dat = rx_dat[:1], rx_dat[1:]
                        if len(self.remote_filter) and (self.rx_bytes[0] not in self.remote_filter):
                            self.logger.debug('byte0 filtered: %02x' % self.rx_bytes[0])
                            self.rx_bytes = b''
                            break
                    if not len(rx_dat):
                        break

                    if len(self.rx_bytes) == 1:
                        self.rx_bytes += rx_dat[:1]
                        rx_dat = rx_dat[1:]
                        if len(self.local_filter) and (self.rx_bytes[1] not in self.local_filter):
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
                            self.out_q.put(_pack(K_FRAME, rx_ts.to_bytes(TS_LEN, 'little') + self.rx_bytes[:-2]))
                            self.rx_bytes = b''

                if len(rx_dat):
                    self.logger.debug('drop left: ' + rx_dat.hex(' '))

            except serial.serialutil.SerialException as err:
                self._online = False
                self._report()
                self.logger.warning(f'{err}')
                self.logger.warning(f're-open: {self.port} ...')
                self.com.close()
                self.echo_dat = None
                self.rx_bytes = b''
                sleep(0.5)

    def send(self, frame):
        self.logger.log(logging.VERBOSE, '<- ' + frame.hex(' ')) # python >= v3.8
        wire = frame + modbus_crc(frame).to_bytes(2, byteorder='little')
        if self.echo:
            self.echo_dat = wire
        # reported before the write: the reply can be read before write() returns
        ts = time_ns().to_bytes(TS_LEN, 'little')
        self.out_q.put(_pack(K_TX, ts + frame))
        try:
            if not self.com: # the port has not been found since open
                raise serial.serialutil.PortNotOpenError()
            self.com.write(wire)
        except serial.serialutil.SerialException as err:
            self.logger.warning(f'send: {err}')
            self.out_q.put(_pack(K_TX_ERR, ts + str(err).encode()))

    def set_baud(self, baud):
        self.baud = baud # a re-open uses it too
        try:
            if self.com:
                self.com.baudrate = baud
        except Exception as err:
            self.logger.warning(f'set baud: {err}')


class _QueueLog(logging.Handler):
    def __init__(self, out_q):
        super().__init__()
        self.out_q = out_q

    def emit(self, record):
        self.out_q.put(_pack(K_LOG, json.dumps([record.name, record.levelno, record.getMessage()]).encode()))


def _forward(out_q):
    while True:
        recs = [out_q.get()]
        while not out_q.empty(): # one write for all that is waiting
            recs.append(out_q.get_nowait())
        view = memoryview(b''.join(recs))
        try:
            while len(view):
                view = view[os.write(1, view):]
        except OSError:
            return # the parent is gone, its end of stdin says so to the main thread


def _child_main():
    signal.signal(signal.SIGINT, signal.SIG_IGN) # ctrl-c reaches us too, the parent's exit closes stdin
    args, level = json.loads(sys.argv[2])
    out_q = queue.Queue() # unbounded: however late the parent is, the port is still read
    logging.getLogger().setLevel(level)
    logging.getLogger().addHandler(_QueueLog(out_q))
    threading.Thread(target=_forward, args=(out_q,), daemon=True).start()

    dev = _SerialWorker(out_q, *args)
    for kind, dat in _read_records(0):
        if kind == K_FRAME:
            dev.send(dat)
        elif kind == K_BAUD:
            dev.set_baud(json.loads(dat))
    os._exit(0) # not a clean shutdown: the port must be free at once for the next instance
