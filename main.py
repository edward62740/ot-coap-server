import asyncio
import ipaddress
import random
import string
import aiocoap
from aiocoap import resource
from server import AlarmResource
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
        root.add_resource((otM.get_child_ips()[ip],), AlarmResource())

    asyncio.Task(aiocoap.Context.create_server_context(root, bind=(addrs[netifaces.AF_INET6][ctr]['addr'], 5683)))
    print("Server running")
    asyncio.get_event_loop().run_until_complete(otM.inform_children())
    asyncio.get_event_loop().run_forever()




if __name__ == "__main__":
    main()
