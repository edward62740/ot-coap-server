import asyncio
import ipaddress
import random
import string
from time import sleep

import aiocoap
from aiocoap import resource
from server import RadarResource
import netifaces
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
    otM.find_child_ips()



    root = resource.Site()
    for ip in otM.get_child_ips():
        root.add_resource((otM.get_child_ips()[ip],), RadarResource(otM.get_child_ips()[ip]))

    asyncio.Task(aiocoap.Context.create_server_context(root, bind=(addrs[netifaces.AF_INET6][ctr]['addr'], 5683)))
    print("Server running")
    # run main task and otM.inform_children() in parallel
    asyncio.get_event_loop().run_until_complete(asyncio.gather(main_task(otM), otM.inform_children()))



async def main_task(otManger: OtManager):
    while True:
        print("finding children")
        otManger.find_child_ips()
        await asyncio.sleep(5)

if __name__ == "__main__":
    main()
