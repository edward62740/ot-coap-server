import ipaddress
import time
import re
import logging
from aiocoap import resource
import aiocoap
import tinytuya

from ot_manager import OtManager
from user_handler import user_handler_callback


class ResourceHandler(resource.Resource):
    """This resource supports the PUT method.
    PUT: Update state of alarm."""

    def __init__(self, uri, ot_mgr: OtManager):
        super().__init__()
        self.coap_payload = None
        self.path = uri
        self.ot_mgr = ot_mgr
        logging.info("Registered resource " + str(uri))


    async def render_put(self, request):
        """ Handles PUT requests, updates info and calls functions to trigger actions. """
        client_ip = request.remote.hostinfo
        self.coap_payload = request.payload.decode("utf-8")
        csv = self.coap_payload.split(",")
        logging.info("Received PUT request from " + str(client_ip) + " with payload " + str(csv))
        logging.warning(csv)
        try:
            if csv[0] == "0": # if is radar
                self.ot_mgr.update_radar(ipaddress.ip_address(re.sub(r"[\[\]]", "", client_ip)), csv)
            elif csv[0] == "1": # if is HS
                self.ot_mgr.update_hs(ipaddress.ip_address(re.sub(r"[\[\]]", "", client_ip)), csv)
        except ValueError:
            logging.warning("Invalid payload")
        user_handler_callback(ipaddress.ip_address(re.sub(r"[\[\]]", "", client_ip)), csv)

        return aiocoap.Message(code=aiocoap.CON)

