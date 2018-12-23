#!/usr/bin/env python3
# Software License Agreement (MIT License)
#
# Copyright (c) 2017, DUKELEC, Inc.
# All rights reserved.
#
# Author: Duke Fong <duke@dukelec.com>
#


import threading
from queue import Queue
from ..utils.log import *
from ..parser import *


SEQ_TX_ACK_CNT = 3
SEQ_TX_RETRY_MAX = 3
_SEQ_TX_PEND_MAX = 6
_SEQ_TIMEOUT = 0.5

# TODO:
#   add router and default_router
#   add multicast registry

class CDNetNS(): # Namespace
    def __init__(self):
        self.intfs = {}     # key: net id
        self.sockets = {}   # key: port num

cdnet_def_ns = CDNetNS()


class CDNetNode(threading.Thread):
    def __init__(self):
        self.logger = logging.getLogger(name)
        
        self.intf = intf
        self.addr = addr
        
        self.rx_seq_num = 0x80
        self.tx_seq_num = 0x80
        self.tx_wait_q
        self.tx_pend_q
        self.send_cnt = 0 # set req_ack for every SEQ_TX_ACK_CNT times
        self.p0_retry_cnt = 0
        self.p0_req = None
        
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
    def __init__(self, dev, net=0, mac=0, ns=cdnet_def_ns):
        self.dev = dev
        self.net = net
        self.mac = mac
        self.ns = ns
        self.logger = logging.getLogger('CDNetIntf {:02x}'.format(net))
        
        # self.multi = {} # SEQ multicast/broadcast address list
        self.nodes = {} # remote device object
        
        assert net not in self.ns.intfs
        self.ns.intfs[net] = self
        
        threading.Thread.__init__(self)
        self.daemon = True
        self.alive = True
        self.start()
    
    def run(self):
        while self.alive:
            frame = self.dev.recv()
            src, dst, dat, seq_val = cdnet_l1.from_frame(frame, self.net)
            # TODO: check dst addr
            if dst[1] not in self.ns.sockets:
                self.logger.warn('port %d not found, drop' % dst[1])
            else:
                sock = self.ns.sockets[dst[1]]
                sock.recv_q.put((dat, src))
    
    def stop(self):
        self.alive = False
        self.join()
    
    def sendto(self, src, dst, data):
        # only support level1 at now
        frame = cdnet_l1.to_frame(src, dst, data, self.mac)
        self.dev.send(frame)


class CDNetSocket():
    def __init__(self, addr, ns=cdnet_def_ns):
        self.ns = ns
        self.port = None
        self.recv_q = Queue()
        
        # bind addr
        assert len(addr) == 2
        assert addr[0] == '' # only allow all address at now
        assert addr[1] in range(1, 0x10000)
        self.port = addr[1]
        assert self.port not in self.ns.sockets
        self.ns.sockets[self.port] = self
    
    def sendto(self, data, addr):
        dst_addr = list(map(lambda x: x and int(x, 16) or 0, addr[0].split(':')))
        assert dst_addr[0] == 0x80 # only support basic level1 at now
        intf = self.ns.intfs[dst_addr[1]]
        src_addr = (dst_addr[0], dst_addr[1], intf.mac)
        src = ':'.join('%02x' % x for x in src_addr)
        return intf.sendto((src, self.port), addr, data)
    
    def recvfrom(self, timeout=None):
        return self.recv_q.get(timeout=timeout)

