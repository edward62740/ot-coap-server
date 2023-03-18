import asyncio  # pylint: disable=import-error
import ipaddress
import logging
import aiocoap
from aiocoap import resource
import aiocoap.numbers.constants
import netifaces
import coloredlogs

import influx_sender
from ot_manager import OtManager
from resource_handler import ResourceHandler
from user_handler import user_handler_init

START_TASK_INFLUX_SENDER = True

COAP_UDP_DEFAULT_PORT = 5683
OT_DEFAULT_PREFIX = "fd74"
OT_DEFAULT_IFACE = "wpan0"

POLL_NEW_CHILDREN_INTERVAL_S = 30

def main(root_res: resource.Site):
    """Main function that starts the server"""
    # Resource tree creation
    aiocoap.numbers.constants.ACK_TIMEOUT = 7.0
    addrs = netifaces.ifaddresses(OT_DEFAULT_IFACE)
    ctr = 0
    for i in addrs[netifaces.AF_INET6]:
        if i["addr"].startswith(OT_DEFAULT_PREFIX):  # ensure binding to mesh-local address
            break
        ctr += 1

    ot_mgr = OtManager(ipaddress.ip_address(addrs[netifaces.AF_INET6][ctr]["addr"]), 1)
    ot_mgr.find_child_ips()

    while (ip := ot_mgr.dequeue_child_ip()) is not None:
        root_res.add_resource(
            (ot_mgr.get_child_ips()[ip].uri,), ResourceHandler(ot_mgr.get_child_ips()[ip].uri, ot_mgr)
        )

    logging.info("Server running")
    user_handler_init()
    asyncio.Task(
        aiocoap.Context.create_server_context(
            root_res, bind=(addrs[netifaces.AF_INET6][ctr]["addr"], COAP_UDP_DEFAULT_PORT)
        )
    )
    asyncio.get_event_loop().run_until_complete(
        asyncio.gather(
            main_task(ot_mgr, root_res), ot_mgr.inform_children(),
            influx_sender.influx_task(ot_mgr) if START_TASK_INFLUX_SENDER else None
        )
    )


async def main_task(ot_manager: OtManager, root_res: resource.Site):
    """Main task that polls for new children and adds them to the resource tree"""
    while True:
        logging.info("Finding new children...")
        ot_manager.find_child_ips()
        ip = ot_manager.dequeue_child_ip()
        while ip is not None:
            try:
                root_res.add_resource(
                    (ot_manager.get_child_ips()[ip].uri,),
                    ResourceHandler(ot_manager.get_child_ips()[ip].uri, ot_manager),
                )
                logging.info(
                    "Added new child " + str(ip) + " with resource " + ot_manager.get_child_ips()[ip].uri
                )
            except KeyError:
                logging.info("Child " + str(ip) + " error")
                pass
            ip = ot_manager.dequeue_child_ip()
        await asyncio.sleep(POLL_NEW_CHILDREN_INTERVAL_S)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    coloredlogs.install(level="INFO")

    coap_root = resource.Site()
    logging.info("Startup success")
    try:
        main(coap_root)
    except KeyboardInterrupt:
        logging.error("Exiting")
