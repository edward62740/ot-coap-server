import ipaddress
import random
import string
import subprocess
import asyncio
from ipaddress import IPv6Address
from typing import Set, Type

import aiocoap
from aiocoap import *
from aiocoap import error


class OtManager:
    child_ip6 = dict[IPv6Address, str]() # Child IPv6 sensitivity list
    pend_queue_child_ips = set[IPv6Address]() # Queue for new children to be notified
    self_ip6 = ipaddress.IPv6Address # CoAP server IPv6

    def __init__(self, self_ip: IPv6Address):
        self.self_ip6 = self_ip
        print("Registered self ip as " + str(self.self_ip6))

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
                        print(line[6:].strip()  + " does not match BR prefix " + prefix)
                    else:
                        tmp = ipaddress.ip_address(line[6:])
                        if tmp not in self.child_ip6:
                            self.pend_queue_child_ips.add(tmp)
                            print(line[6:].strip()  + " added to child notif queue")
                            x = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                            self.child_ip6[tmp] = x
                            print(line[6:].strip()  + " updated in child sensitivity list with resource " + x)
                except ValueError:
                    pass

            last = str(process.poll())
            if last is not None:
                break

    def get_child_ips(self) -> dict[IPv6Address]:
        return self.child_ip6

    def deque_child_ips(self):
        if self.pend_queue_child_ips.__len__() > 0:
            return self.pend_queue_child_ips
        else:
            return None


    async def inform_children(self):
        while True:
            if self.deque_child_ips() is not None:
                await asyncio.gather(*[self._inform(ip) for ip in self.deque_child_ips()])
            await asyncio.sleep(1)

    async def _inform(self, ip: IPv6Address):
        try:
            print("Sending to " + str(ip))
            context = await Context.create_client_context()
            payload = str.encode(self.child_ip6[ip])
            request = Message(code=GET, payload=payload, uri="coap://[" + str(ip) + "]/permissions")
            response = await context.request(request).response
            print('Result: %x\n%r' % (response.code, response.payload))
            try:
                self.deque_child_ips().remove(ip)
            except KeyError:
                print("child disappeared suddenly")
                pass
        except aiocoap.error.ConRetransmitsExceeded:
            print("child not reachable")
            pass
