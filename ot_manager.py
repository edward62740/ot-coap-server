import ipaddress
import random
import string
import subprocess
import asyncio

from ipaddress import IPv6Address

from dataclasses import dataclass, field

import aiocoap
from aiocoap import *
from aiocoap import error

import logging


@dataclass
class OtDevice:
    uri: str = field(default="")
    det_flag: bool = field(default=False)
    det_conf: int = field(default=0)
    det_dist: int = field(default=0)
    det_lux: int = field(default=0)
    last_seen: int = field(default=0)


class OtManager:
    child_ip6 = dict[IPv6Address, OtDevice]() # Child IPv6 sensitivity list
    pend_queue_res_child_ips = set[IPv6Address]() # Queue for new children to be allocated a resource
    _pend_queue_notif_child_ips = set[IPv6Address]() # Queue for new children to be notified of their resource
    self_ip6 = ipaddress.IPv6Address # CoAP server IPv6

    def __init__(self, self_ip: IPv6Address):
        self.self_ip6 = self_ip
        logging.info("Registered self ip as " + str(self.self_ip6))

    def find_child_ips(self) -> None:
        process = subprocess.Popen(['ot-ctl', 'childip'],
                                   stdout=subprocess.PIPE,
                                   universal_newlines=True)
        while True:
            output = process.stdout.readlines()
            lines = output
            prefix = str(self.self_ip6)[:4]
            for line in lines:
                try:
                    line = line.rstrip()
                    if not line[6:].startswith(prefix):
                        logging.info(line[6:].strip()  + " does not match mesh-local prefix " + prefix)
                    else:
                        tmp = ipaddress.ip_address(line[6:])
                        if tmp not in self.child_ip6:
                            self.pend_queue_res_child_ips.add(tmp)
                            logging.info(line[6:].strip()  + " added to child notif queue")
                            x = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                            self.child_ip6[tmp] = OtDevice(uri=x)
                            logging.info(line[6:].strip()  + " updated in child sensitivity list with resource " + x)
                except ValueError:
                    pass

            last = str(process.poll())
            if last is not None:
                break

    def get_child_ips(self):
        return self.child_ip6

    def dequeue_child_ip(self):
        try:
            tmp = self.pend_queue_res_child_ips.pop()
            self._pend_queue_notif_child_ips.add(tmp)
            return tmp
        except KeyError:
            return None
    def _get_queued_child_ips(self):
        if self._pend_queue_notif_child_ips.__len__() > 0:
            return self._pend_queue_notif_child_ips
        else:
            return None

    async def inform_children(self, interval=15):
        while True:
            if self._get_queued_child_ips() is not None:
                await asyncio.gather(*[self._inform(ip) for ip in self._get_queued_child_ips()])
                logging.info("Notified children" + str(self._get_queued_child_ips()))
            await asyncio.sleep(interval)

    async def _inform(self, ip: IPv6Address):
        try:
            logging.info("Sending to " + str(ip))
            context = await Context.create_client_context()
            payload = str.encode(self.child_ip6[ip].uri)
            request = Message(code=GET, payload=payload, uri="coap://[" + str(ip) + "]/permissions")
            response = await context.request(request).response
            logging.info('Result: %x\n%r' % (response.code, response.payload))
            try:
                self._get_queued_child_ips().remove(ip)
            except KeyError:
                logging.warning("Child " + str(ip) + " disappeared suddenly")
                pass
        except aiocoap.error.ConRetransmitsExceeded:
            logging.warning("Child " + str(ip) + " not reachable")
            pass
