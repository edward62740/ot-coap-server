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
    root = resource.Site()
    root.add_resource(['radar'], AlarmResource())
    ctr = 0
    for i in addrs[netifaces.AF_INET6]:
        ctr+=1
        if i['addr'].startswith('fd'):
            break
    print(addrs[netifaces.AF_INET6][ctr]['addr'])
    process = subprocess.Popen(['ot-ctl', 'childip'],
                           stdout=subprocess.PIPE,
                           universal_newlines=True)
    while True:
        output = process.stdout.readline()
        print(output.strip())
        # Do something else
        return_code = process.poll()
        if return_code is not None:
                print('RETURN CODE', return_code)
                # Process has finished, read rest of the output
                for output in process.stdout.readlines():
                        print(output.strip())
                break
    asyncio.get_event_loop().run_until_complete(client())
    asyncio.Task(aiocoap.Context.create_server_context(root, bind=(addrs[netifaces.AF_INET6][ctr]['addr'], 5683)))

    asyncio.get_event_loop().run_forever()



async def client():
    context = await Context.create_client_context()
    payload = b"000000"

    request = Message(code=GET, payload=payload, uri="coap://[fd55:6a16:72dc:1:7ac4:81b4:ef1a:1028]/permissions")

    response = await context.request(request).response
    print('Result: %x\n%r' % (response.code, response.payload))




if __name__ == "__main__":
    main()
