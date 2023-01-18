import enum
import ipaddress
import random
import string
import subprocess
import asyncio
import time

from ipaddress import IPv6Address

from dataclasses import dataclass, field
import logging
import aiocoap
from aiocoap import *

OT_DEVICE_TIMEOUT_CYCLES = 5
class OtDeviceType(enum.IntEnum):
    RADAR = 0
    HS = 1
    UNKNOWN = -255

@dataclass
class OtDevice:
    """ Generic class for an OpenThread device. """
    device_type: OtDeviceType = field(default=OtDeviceType.UNKNOWN)
    eui64: int = field(default=0)
    uri: str = field(default="")
    last_seen: float = field(default=0)
    timeout_cyc: int = field(default=OT_DEVICE_TIMEOUT_CYCLES)
    ctr: int = field(default=0)

@dataclass
class OtRadar(OtDevice):
    """ Class to store information about a radar device. """
    radar_flag: bool = field(default=False)
    radar_conf: int = field(default=0)
    radar_dist: int = field(default=0)
    opt_lux: int = field(default=0)
    vdd: int = field(default=0)
    rssi: int = field(default=0)

@dataclass
class OtHs(OtDevice):
    pass # NOT IMPLEMENTED YET


class OtManager:
    """ This class manages the ot children and associated information.
    New children are found by calling find_child_ips() and added to the sensitivity list.
    Children that do not have a resource associated with them are added to the res queue,
    and also placed into the notification queue to be notified of their resource uri """

    child_ip6 = dict[IPv6Address, OtDevice]() # Child IPv6 sensitivity list
    pend_queue_res_child_ips = set[IPv6Address]() # Queue for new children to be allocated a resource
    _pend_queue_notif_child_ips = set[IPv6Address]() # Queue for new children to be notified of their resource
    self_ip6 = ipaddress.IPv6Address # CoAP server IPv6

    def __init__(self, self_ip: IPv6Address):
        self.self_ip6 = self_ip
        logging.info("Registered self ip as " + str(self.self_ip6))

    def find_child_ips(self) -> None:
        """ Checks from ot-ctl if there are new children and adds them to the sensitivity list """
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
                        logging.info(line[6:].strip()  + " does not match mesh-local prefix " + prefix)
                    else:
                        tmp = ipaddress.ip_address(line[6:])
                        if tmp not in self.child_ip6:
                            self.pend_queue_res_child_ips.add(tmp)
                            logging.info(line[6:].strip()  + " added to child notif queue")
                            tmp_uri = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                            self.child_ip6[tmp] = OtDevice(uri=tmp_uri)
                            logging.info(line[6:].strip()  + " updated in child sensitivity list with resource " + tmp_uri)
                except ValueError:
                    pass
            last = str(process.poll())
            if last is not None:
                break

    def get_child_ips(self):
        """ Returns a dict of all children in the sensitivity list """
        return self.child_ip6

    def update_child_info(self, ip: IPv6Address, ls: float):
        """ Updates the sensitivity list with new information from the child """
        try:
            self.child_ip6[ip].last_seen = ls
            self.child_ip6[ip].timeout_cyc = OT_DEVICE_TIMEOUT_CYCLES

        except KeyError:
            logging.warning("Child " + str(ip) + " not found in sensitivity list")
            raise ValueError

    def update_radar(self, ip: IPv6Address, csv: list):
        """ Updates the radar sensitivity list with new information from the child """
        try:
            flag = False if csv[2] == "0" else True if csv[2] == "1" else None
            if not isinstance(self.child_ip6[ip], OtRadar):
                self.child_ip6[ip] = OtRadar(device_type=OtDeviceType.RADAR, eui64=csv[1], radar_flag=flag, radar_conf=csv[3],
                                             radar_dist=csv[4],opt_lux=csv[5], vdd=csv[6], rssi=csv[7])
            else:
                if flag is not None:
                    self.child_ip6[ip].radar_flag = flag
                self.child_ip6[ip].radar_conf = csv[3]
                self.child_ip6[ip].radar_dist = csv[4]
                self.child_ip6[ip].opt_lux = csv[5]
                self.child_ip6[ip].vdd = csv[6]
                self.child_ip6[ip].rssi = csv[7]
                self.child_ip6[ip].ctr = csv[8]
            self.update_child_info(ip, time.time())

        except KeyError:
            logging.warning("Child " + str(ip) + " not found in sensitivity list")
            raise ValueError

    def dequeue_child_ip(self):
        """ Returns a child IP from the res queue and removes it from the queue, if empty returns None """
        try:
            tmp = self.pend_queue_res_child_ips.pop()
            self._pend_queue_notif_child_ips.add(tmp)
            return tmp
        except KeyError:
            return None

    def _get_queued_child_ips(self):
        """ Returns a set of child IPs from the notif queue if the set is not empty, if empty returns None """
        return self._pend_queue_notif_child_ips

    async def inform_children(self, interval=15):
        """ Sends a notification to all children in the notif queue """
        while True:
            if len(self._get_queued_child_ips()) > 0:
                await asyncio.gather(*[self._inform(ip) for ip in self._get_queued_child_ips()])
                logging.info("Notified children")
            # inform children if last seen > 15 seconds before now
            child_ipv6_tmp = self.child_ip6.copy()
            for ip in child_ipv6_tmp:
                if self.child_ip6[ip].last_seen + 100 < time.time() and self.child_ip6[ip].last_seen != 0:
                    self.child_ip6[ip].timeout_cyc -= 1
                    if self.child_ip6[ip].timeout_cyc == 0:
                        logging.info("Child " + str(ip) + " timed out")
                        del self.child_ip6[ip]
                        continue
                    await self._inform(ip)
                    # print how long child was seen ago in seconds
                    logging.info("Due to inactivity, notified child " + str(ip) + " last seen " + str(time.time() - self.child_ip6[ip].last_seen) + " seconds ago")
            await asyncio.sleep(interval)

    async def _inform(self, ip: IPv6Address):
        """ Sends a notification to a single child """
        try:
            logging.info("Sending to " + str(ip))
            context = await Context.create_client_context()
            try:
                payload = str.encode(self.child_ip6[ip].uri)
            except KeyError:
                logging.warning("Child " + str(ip) + " not found in sensitivity list")
            request = Message(code=GET, payload=payload, uri="coap://[" + str(ip) + "]/permissions")
            response = await context.request(request).response
            logging.info("Client responded with: " + str(response.payload))
            try:
                self._get_queued_child_ips().remove(ip)
            except (KeyError, AttributeError):
                logging.warning("Child " + str(ip) + " disappeared suddenly")

        except aiocoap.error.ConRetransmitsExceeded:
            logging.warning("Child " + str(ip) + " not reachable")

