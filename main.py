import asyncio
import ipaddress

import aiocoap
from aiocoap import *
from aiocoap import resource

from server import AlarmResource
import netifaces
import subprocess
from ot_manager import OtManager

def main():
    # Resource tree creation
    addrs = netifaces.ifaddresses('wpan0')

    ctr = 0
    for i in addrs[netifaces.AF_INET6]:
        ctr+=1
        if i['addr'].startswith('fd'):
            break
    otM = OtManager(ipaddress.ip_address(addrs[netifaces.AF_INET6][ctr]['addr']))
    otM.findChildIps()
    ips = otM.getChildIps()

    asyncio.get_event_loop().run_until_complete(client(otM))
    root = resource.Site()
    root.add_resource(['radar'], AlarmResource())
    asyncio.Task(aiocoap.Context.create_server_context(root, bind=(addrs[netifaces.AF_INET6][ctr]['addr'], 5683)))
    print("Server running")
    asyncio.get_event_loop().run_forever()


async def client(otm: OtManager):
    context = await Context.create_client_context()
    payload = b"000000"
    while True:
        ip = otm.dequePendChildIps()
        if ip != ipaddress.IPv6Address("::"):
            print("Sent to %s" % ip)
            request = Message(code=GET, payload=payload, uri="coap://[" + str(ip) + "]/permissions")
        else:
            break

        response = await context.request(request).response
        print('Result: %x\n%r' % (response.code, response.payload))




if __name__ == "__main__":
    main()
