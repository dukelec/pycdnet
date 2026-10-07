#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2026, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>

"""Write CDBUS frames to a pcapng file, for Wireshark with the cdbus.lua dissector of
https://github.com/dukelec/cdbus_tools (wireshark/Readme.md there describes the format).

The file has two interfaces, nanosecond timestamps since the epoch:
  0 "cdbus", link type USER0 (147): one frame per packet as it is on the wire, header,
    payload and crc; the epb flags give the direction, 1 inbound (from the bus), 2 outbound
  1 "mark",  link type USER1 (148): a mark, its text as the packet data and as the comment,
    so it reads the same with or without the dissector

Every block is one unbuffered write(), so a process that dies at any point leaves whole blocks
behind and nothing to flush. packet() may be called from any thread.

    w = PcapngWriter('cdbus_20260101_120000.pcapng', app='cdbus_terminal', dev_str='/dev/ttyACM0 @ 115200')
    w.packet(IF_CDBUS, frame_with_crc, flags=FLAG_OUTBOUND)   # ts_ns: now, unless given
    w.packet(IF_MARK, b'motor on', comment='motor on')
    w.close()
"""

import struct
import time
import platform
import threading

__all__ = ['PcapngWriter', 'LINKTYPE_USER0', 'LINKTYPE_USER1', 'IF_CDBUS', 'IF_MARK',
           'FLAG_INBOUND', 'FLAG_OUTBOUND', 'BT_SHB', 'BT_IDB', 'BT_EPB', 'OPT_END', 'OPT_COMMENT',
           'SHB_OS', 'SHB_USERAPPL', 'IF_NAME', 'IF_DESCRIPTION', 'IF_TSRESOL', 'EPB_FLAGS']

LINKTYPE_USER0 = 147
LINKTYPE_USER1 = 148

IF_CDBUS = 0
IF_MARK = 1

FLAG_INBOUND = 1    # epb_flags direction: the frame came in from the bus
FLAG_OUTBOUND = 2   # the writer sent it

# pcapng block and option codes
BT_SHB = 0x0a0d0d0a
BT_IDB = 1
BT_EPB = 6
OPT_END = 0
OPT_COMMENT = 1
SHB_OS = 3
SHB_USERAPPL = 4
IF_NAME = 2
IF_DESCRIPTION = 3
IF_TSRESOL = 9
EPB_FLAGS = 2


def _opt(code, val):
    """one option, value padded to 4 bytes; a str goes in as utf-8"""
    if isinstance(val, str):
        val = val.encode()
    return struct.pack('<HH', code, len(val)) + val + b'\0' * (-len(val) % 4)


def _block(btype, body, opts=b''):
    if opts:
        opts += _opt(OPT_END, b'')
    body += opts
    total = 12 + len(body)
    return struct.pack('<II', btype, total) + body + struct.pack('<I', total)


class PcapngWriter:
    """a pcapng file with the two interfaces above, every block one write() as it comes.
    app: goes into shb_userappl, the writer's name; dev_str: the port, baud rate and local address,
    into the cdbus interface's description; mark_str: where the marks come from, into the mark's"""

    def __init__(self, path, app='cdnet', comment=None, dev_str=None, mark_str=None):
        self.path = path
        self.f = open(path, 'wb', buffering=0)
        self.lock = threading.Lock()
        self.size = 0
        opts = _opt(SHB_USERAPPL, app) + _opt(SHB_OS, platform.platform())
        if comment:
            opts = _opt(OPT_COMMENT, comment) + opts
        self._write(_block(BT_SHB, struct.pack('<IHHq', 0x1a2b3c4d, 1, 0, -1), opts))
        self._write(self._idb(LINKTYPE_USER0, 'cdbus',
                              f'CDBUS frames: {dev_str}' if dev_str else 'CDBUS frames'))
        self._write(self._idb(LINKTYPE_USER1, 'mark', mark_str or 'marks'))

    @staticmethod
    def _idb(linktype, name, desc):
        opts = _opt(IF_NAME, name) + _opt(IF_DESCRIPTION, desc) + _opt(IF_TSRESOL, b'\x09')
        return _block(BT_IDB, struct.pack('<HHI', linktype, 0, 0), opts)

    def _write(self, blk):
        if self.f.write(blk) != len(blk): # unbuffered: a block is in the file whole, or not at all
            raise OSError(f'short write to {self.path}')
        self.size += len(blk)

    def packet(self, if_id, dat, ts_ns=None, flags=None, comment=None):
        """one packet on interface if_id, stamped now unless ts_ns is given"""
        if ts_ns is None:
            ts_ns = time.time_ns()
        opts = b''
        if comment:
            opts += _opt(OPT_COMMENT, comment)
        if flags is not None:
            opts += _opt(EPB_FLAGS, struct.pack('<I', flags))
        body = struct.pack('<IIIII', if_id, ts_ns >> 32, ts_ns & 0xffffffff, len(dat), len(dat))
        body += dat + b'\0' * (-len(dat) % 4)
        with self.lock:
            self._write(_block(BT_EPB, body, opts))

    def close(self):
        self.f.close()
