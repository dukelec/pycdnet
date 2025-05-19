#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <d@d-l.io>
#


import threading
from queue import Queue, Empty
from ..utils.log import *
from ..parser import *


# TODO:
#   add router and default_router
#   add multicast registry

class CDNetNS(): # Namespace
    def __init__(self):
        self.intfs = {}     # key: net id
        self.sockets = {}   # key: port num

cdn_def_ns = CDNetNS()


class CDNetNode(threading.Thread):
    def __init__(self):
        self.logger = logging.getLogger(name)

        self.intf = intf
        self.addr = addr

        threading.Thread.__init__(self)
        self.daemon = True
        self.alive = True
        self.start()

    def run(self):
        while self.alive:
            pass

    def stop(self):
        self.alive = False
        self.join()


class CDNetIntf(threading.Thread):
    def __init__(self, dev, net=0, mac=0, ns=cdn_def_ns):
        self.dev = dev
        self.net = net
        self.mac = mac
        self.ns = ns
        self.logger = logging.getLogger(f'cdnet.intf.0x{net:02x}')

        assert net not in self.ns.intfs
        self.ns.intfs[net] = self

        threading.Thread.__init__(self)
        self.daemon = True
        self.alive = True
        self.start()

    def run(self):
        while self.alive:
            frame = self.dev.recv()
            if frame[3] & 0x80:
                src, dst, dat = cdnet_l1.from_frame(frame, self.net)
            else:
                src, dst, dat = cdnet_l0.from_frame(frame, self.net)
            # TODO: check dst addr
            if dst[1] not in self.ns.sockets:
                self.logger.warning('port %d not found, drop' % dst[1])
            else:
                sock = self.ns.sockets[dst[1]]
                sock.recv_q.put((dat, src))

    def stop(self):
        self.alive = False
        self.join()

    def sendto(self, src, dst, data):
        if src[0].startswith('00:'):
            frame = cdnet_l0.to_frame(src, dst, data)
        else:
            frame = cdnet_l1.to_frame(src, dst, data, self.mac, int(dst[0].split(':')[2], 16))
        self.dev.send(frame)


class CDNetSocket():
    def __init__(self, addr, ns=cdn_def_ns):
        self.ns = ns
        self.port = None
        self.recv_q = Queue()

        # bind addr
        assert len(addr) == 2
        assert addr[0] == '' # only allow all address at now
        assert addr[1] in range(0, 0x10000)
        self.port = addr[1]
        assert self.port not in self.ns.sockets
        self.ns.sockets[self.port] = self

    def sendto(self, data, addr):
        dst_addr = list(map(lambda x: x and int(x, 16) or 0, addr[0].split(':')))
        intf = self.ns.intfs[dst_addr[1]]
        src_addr = (dst_addr[0], dst_addr[1], intf.mac)
        src = ':'.join('%02x' % x for x in src_addr)
        return intf.sendto((src, self.port), addr, data)

    def recvfrom(self, timeout=None):
        try:
            return self.recv_q.get(timeout=timeout)
        except Empty:
            return None, None

    def clear(self):
        with self.recv_q.mutex:
            self.recv_q.queue.clear()

