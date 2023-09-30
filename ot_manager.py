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
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf


OT_DEVICE_TIMEOUT_CYCLES = 5
OT_DEVICE_CHILD_TIMEOUT_S = 190
OT_DEVICE_CHILD_TIMEOUT_CYCLE_RATE = 1
OT_DEVICE_POLL_INTERVAL_S = 5

class OtDeviceType(enum.IntEnum):
    RADAR = 0
    HS = 1
    CO2 = 2
    GASSENTINEL = 254
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
    temp_main: int = field(default=0)
    temp_aux: int = field(default=0)
    hum_main: int = field(default=0)
    ret: int = field(default=0)
    state: int = field(default=0)
    vdd: int = field(default=0)
    rssi: int = field(default=0)

@dataclass
class OtCo2sn(OtDevice):
    co2: int = field(default=0)
    temp: int = field(default=0)
    hum: int = field(default=0)
    error: int = field(default=0)
    offset: int = field(default=0)
    age: int = field(default=0)
    num: int = field(default=0)
    vdd: int = field(default=0)
    rssi: int = field(default=0)

@dataclass
class GasSentinel(OtDevice):
    iaq: int = field(default=0)
    temp: int = field(default=0)
    hum: int = field(default=0)
    pres: int = field(default=0)
    cl1: int = field(default=0)
    cl2: int = field(default=0)
    vdd: int = field(default=0)
    rssi: int = field(default=0)


class OtManager:
    """ This class manages the ot children and associated information.
    New children are found by calling find_child_ips() and added to the sensitivity list.
    Children that do not have a resource associated with them are added to the res queue,
    and also placed into the notification queue to be notified of their resource uri """

    child_ip6 = dict[IPv6Address, OtDevice]() # Child IPv6 sensitivity list
    pend_queue_res_child_ips = set[IPv6Address]() # Queue for new children to be allocated a resource
    _pend_queue_notif_child_ips = set[IPv6Address]() # Queue for new children to be notified of their resource
    _pend_cb_dns_sd_new_ips = set[IPv6Address]()
    self_ip6 = ipaddress.IPv6Address # CoAP server IPv6
    _option_find_ips = 0
    def __init__(self, self_ip: IPv6Address, option_find_ips = 0):
        self.self_ip6 = self_ip
        if option_find_ips != 0:
            self._option_find_ips = 1
            zeroconf = Zeroconf()
            listener = self.DnsSdListener()
            browser = ServiceBrowser(zeroconf, "_ot._udp.local.", listener)
        logging.info("Registered self ip as " + str(self.self_ip6))

    class DnsSdListener(ServiceListener):
        """ Listener for DNS-SD services """
        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            logging.info(f"Service {name} added, service info: {info}")
            try:
                ip = info._ipv6_addresses[0]
                OtManager._pend_cb_dns_sd_new_ips.add(ip)
            except Exception as e:
                pass

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            logging.info(f"Service {name} updated, service info: {info}")
            return
            try:
                ip = info._ipv6_addresses[0]
                OtManager._pend_cb_dns_sd_new_ips.add(ip)
            except Exception as e:
                pass
        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            pass


    def find_child_ips(self) -> None:
        if self._option_find_ips == 0:
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
        else:
            while len(self._pend_cb_dns_sd_new_ips) > 0:
                ip = self._pend_cb_dns_sd_new_ips.pop()
                if ip not in OtManager.child_ip6:
                    OtManager.pend_queue_res_child_ips.add(ip)
                    logging.info(str(ip) + " added to child notif queue")
                    tmp_uri = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                    OtManager.child_ip6[ip] = OtDevice(uri=tmp_uri)
                    logging.info(str(ip) + " updated in child sensitivity list with resource " + tmp_uri)



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
            try:
                OtManager._pend_cb_dns_sd_new_ips.add(ip)
            except Exception as e:
                pass
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
            try:
                OtManager._pend_cb_dns_sd_new_ips.add(ip)
            except Exception as e:
                pass
            logging.warning("Child " + str(ip) + " not found in sensitivity list")
            raise ValueError

    def update_hs(self, ip: IPv6Address, csv: list):
        """ Updates the radar sensitivity list with new information from the child """
        try:
            if not isinstance(self.child_ip6[ip], OtHs):
                self.child_ip6[ip] = OtHs(device_type=OtDeviceType.HS, eui64=csv[1], temp_main=csv[2], hum_main=csv[3],
                                             temp_aux=csv[4],ret=csv[5], state=csv[6], vdd=csv[7])
            else:
                self.child_ip6[ip].temp_main = csv[2]
                self.child_ip6[ip].hum_main = csv[3]
                self.child_ip6[ip].temp_aux = csv[4]
                self.child_ip6[ip].ret = csv[5]
                self.child_ip6[ip].state = csv[6]
                self.child_ip6[ip].vdd = csv[7]
            self.update_child_info(ip, time.time())

        except KeyError:
            try:
                OtManager._pend_cb_dns_sd_new_ips.add(ip)
            except Exception as e:
                pass
            logging.warning("Child " + str(ip) + " not found in sensitivity list")
            raise ValueError


    def update_gassentinel(self, ip: IPv6Address, csv: list):
        """ Updates the radar sensitivity list with new information from the child """
        try:
            if not isinstance(self.child_ip6[ip], GasSentinel):
                self.child_ip6[ip] = GasSentinel(device_type=OtDeviceType.GASSENTINEL, eui64=csv[1], iaq=csv[2], temp=csv[3], hum=csv[4], pres=csv[5], cl1=csv[6], cl2=csv[7], rssi=csv[8], vdd=csv[9])
            else:
                self.child_ip6[ip].iaq = csv[2]
                self.child_ip6[ip].temp = csv[3]
                self.child_ip6[ip].hum = csv[4]
                self.child_ip6[ip].pres = csv[5]

                if int(csv[6]) != 0 and int(csv[7]) != 0:
                    self.child_ip6[ip].cl1 = csv[6]
                    self.child_ip6[ip].cl2 = csv[7]

                self.child_ip6[ip].rssi = csv[8]
                self.child_ip6[ip].vdd = csv[9]
            self.update_child_info(ip, time.time())

        except KeyError:
            try:
                OtManager._pend_cb_dns_sd_new_ips.add(ip)
            except Exception as e:
                pass
            logging.warning("Child " + str(ip) + " not found in sensitivity list")
            raise ValueError


    def update_co2(self, ip: IPv6Address, csv: list):
        """ Updates the radar sensitivity list with new information from the child """
        try:
            if not isinstance(self.child_ip6[ip], OtCo2sn):
                self.child_ip6[ip] = OtCo2sn(device_type=OtDeviceType.CO2, eui64=csv[1])
                self._update_co2_int(ip, csv)

            else:
                self._update_co2_int(ip, csv)
            self.update_child_info(ip, time.time())

        except KeyError:
            try:
                OtManager._pend_cb_dns_sd_new_ips.add(ip)
            except Exception as e:
                pass
            logging.warning("Child " + str(ip) + " not found in sensitivity list")
            raise ValueError

    def _update_co2_int(self, ip: IPv6Address, csv: list):
        if csv.__len__() == 5:
            self.child_ip6[ip].vdd = csv[2]
            self.child_ip6[ip].rssi = csv[3]
            self.child_ip6[ip].ctr = csv[4]
        elif csv.__len__() == 12:
            self.child_ip6[ip].co2 = csv[3]
            self.child_ip6[ip].error = csv[2]
            self.child_ip6[ip].temp = csv[4]
            self.child_ip6[ip].hum = csv[5]
            self.child_ip6[ip].offset = csv[6]
            self.child_ip6[ip].age = csv[7]
            self.child_ip6[ip].num = csv[8]
            self.child_ip6[ip].vdd = csv[9]
            self.child_ip6[ip].rssi = csv[10]
            self.child_ip6[ip].ctr = csv[11]

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

    async def inform_children(self, interval=OT_DEVICE_POLL_INTERVAL_S):
        """ Sends a notification to all children in the notif queue """
        while True:
            if len(self._get_queued_child_ips()) > 0:
                await asyncio.gather(*[self._inform(ip) for ip in self._get_queued_child_ips()])
                logging.info("Notified children")
            # inform children if last seen > 100 seconds before now
            child_ipv6_tmp = self.child_ip6.copy()
            for ip in child_ipv6_tmp:
                if self.child_ip6[ip].last_seen + OT_DEVICE_CHILD_TIMEOUT_S < time.time() and self.child_ip6[ip].last_seen != 0:
                    self.child_ip6[ip].timeout_cyc -= OT_DEVICE_CHILD_TIMEOUT_CYCLE_RATE
                    if self.child_ip6[ip].timeout_cyc == 0:
                        logging.info("Child " + str(ip) + " timed out")
                        del self.child_ip6[ip]
                        continue
                    await self._inform(ip)
                    # log how long child was seen ago in seconds
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
                try:
                    OtManager._pend_cb_dns_sd_new_ips.add(ip)
                except Exception as e:
                    pass
                logging.warning("Child " + str(ip) + " not found in sensitivity list")
            except (OSError, aiocoap.error.NetworkError):
                logging.warning("Network error")

            request = Message(code=GET, payload=payload, uri="coap://[" + str(ip) + "]/permissions")
            response = await context.request(request).response
            logging.info("Client responded with: " + str(response.payload))
            try:
                self._get_queued_child_ips().remove(ip)
            except (KeyError, AttributeError):
                logging.warning("Child " + str(ip) + " disappeared suddenly")

        except (aiocoap.error.ConRetransmitsExceeded, aiocoap.error.NetworkError):
            logging.warning("Child " + str(ip) + " not reachable")
