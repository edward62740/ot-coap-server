import asyncio
import ipaddress

import aiocoap
from aiocoap import *
from aiocoap import resource

from server import AlarmResource
import netifaces
import subprocess

def main():
    # Resource tree creation
    addrs = netifaces.ifaddresses('wpan0')

    ctr = 0
    for i in addrs[netifaces.AF_INET6]:
        ctr+=1
        if i['addr'].startswith('fd'):
            break

    process = subprocess.Popen(['ot-ctl', 'childip'],
                           stdout=subprocess.PIPE,
                           universal_newlines=True)
    ips = []
    while True:
        output = process.stdout.readline()
        lines = output.strip().splitlines()
        for line in lines:
            try:
                print(line[6:])
                tmp = ipaddress.ip_address(line[6:])
                ips.append(tmp)
            except ValueError:
                pass


        print(ips)
        # Do something else
        return_code = process.poll()
        if return_code is not None:
            break

    asyncio.get_event_loop().run_until_complete(client(ips))
    print("SERVER IP" + addrs[netifaces.AF_INET6][ctr]['addr'])
    root = resource.Site()
    root.add_resource(['radar'], AlarmResource())
    asyncio.Task(aiocoap.Context.create_server_context(root, bind=(addrs[netifaces.AF_INET6][ctr]['addr'], 5683)))
    print("Server running")
    asyncio.get_event_loop().run_forever()
    print("This is the end")


async def client(ips: list[ipaddress.IPv6Address]):
    context = await Context.create_client_context()
    payload = b"000000"

    for ip in ips:
        print("Sent to %s" % ip)
        request = Message(code=GET, payload=payload, uri="coap://[" + str(ip) + "]/permissions")

        response = await context.request(request).response
        print('Result: %x\n%r' % (response.code, response.payload))




if __name__ == "__main__":
    main()
