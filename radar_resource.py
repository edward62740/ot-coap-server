import ipaddress
import time
import re

import aiocoap.resource as resource
import aiocoap
import tinytuya
import logging
from ot_manager import OtManager

class RadarResource(resource.Resource):
    """This resource supports the PUT method.
    PUT: Update state of alarm."""


    def __init__(self, uri, ot_mgr: OtManager):
        super().__init__()
        self.path = uri
        self.ot_mgr = ot_mgr
        logging.info("Registered resource " + str(uri))
        self.state = "OFF"
        self.bulb1.set_version(3.3)
        self.bulb2.set_version(3.3)
        self.bulb3.set_version(3.3)

    async def render_put(self, request):
        """ Handles PUT requests, updates info and calls functions to trigger actions. """
        client_ip = request.remote.hostinfo
        self.state = request.payload.decode("utf-8")
        csv = self.state.split(",")
        logging.warning(csv)
        try:
            self.ot_mgr.update_child_info(ipaddress.ip_address(re.sub(r"[\[\]]", "", client_ip)),
                                          int(csv[1]), int(csv[2]), int(csv[3]), int(csv[4]), int(csv[5]), time.time(), int(csv[6]), False if csv[0] == "0" else True if csv[0] == "1" else None)
        except ValueError:
            logging.warning("Invalid payload")
            pass
        logging.info("Received PUT request from " + client_ip + " with payload " + self.state)
        if csv[0] == "1":
            self.bulb1.turn_on()
            self.bulb2.turn_on()
            self.bulb3.turn_on()

        if csv[0] == "0":
            self.bulb1.turn_off()
            self.bulb2.turn_off()
            self.bulb3.turn_off()
        return aiocoap.Message(code=aiocoap.ACK)