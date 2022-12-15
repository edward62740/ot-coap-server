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
import logging
import coloredlogs

COAP_UDP_DEFAULT_PORT = 5683
OT_DEFAULT_PREFIX = 'fd'
OT_DEFAULT_IFACE = "wpan0"
def main(root_res: resource.Site):
    # Resource tree creation
    addrs = netifaces.ifaddresses(OT_DEFAULT_IFACE)
    ctr = 0
    for i in addrs[netifaces.AF_INET6]:
        ctr+=1
        if i['addr'].startswith(OT_DEFAULT_PREFIX): # ensure binding to mesh-local address
            break
    ot_mgr = OtManager(ipaddress.ip_address(addrs[netifaces.AF_INET6][ctr]['addr']))
    ot_mgr.find_child_ips()

    while (ip:= ot_mgr.dequeue_child_ip()) is not None:
        root_res.add_resource((ot_mgr.get_child_ips()[ip].uri,), RadarResource(ot_mgr.get_child_ips()[ip].uri))

    logging.info("Server running")
    asyncio.Task(aiocoap.Context.create_server_context(root_res, bind=(addrs[netifaces.AF_INET6][ctr]['addr'], COAP_UDP_DEFAULT_PORT)))
    asyncio.get_event_loop().run_until_complete(asyncio.gather(main_task(ot_mgr, root_res), ot_mgr.inform_children()))


async def main_task(ot_manager: OtManager, root_res: resource.Site):
    while True:
        logging.info("Finding new children...")
        ot_manager.find_child_ips()
        # TODO: Render request raised a renderable error (NotFound()), responding accordingly.
        ip = ot_manager.dequeue_child_ip()
        if ip is not None:
            try:
                root_res.add_resource((ot_manager.get_child_ips()[ip].uri,), RadarResource(ot_manager.get_child_ips()[ip].uri))
                logging.info("Added new child " + str(ip) + " with resource " + ot_manager.get_child_ips()[ip].uri)
            except KeyError:
                pass
        await asyncio.sleep(5)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    coloredlogs.install(level='INFO')

    coap_root = resource.Site()
    logging.info("Startup success")
    try:
        main(coap_root)
    except KeyboardInterrupt:
        logging.error("Exiting")

