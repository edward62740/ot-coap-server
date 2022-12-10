import ipaddress
import subprocess
import asyncio
from ipaddress import IPv6Address
from typing import Set, Type


class OtManager:
    child_ip6 = set[IPv6Address]() # Child IPv6 sensitivity list
    pend_queue_child_ips = set[IPv6Address]() # Queue for new children to be notified
    self_ip6 = ipaddress.IPv6Address # CoAP server IPv6

    def __init__(self, self_ip: Type[IPv6Address]):
        self.self_ip6 = self_ip
        print("Registered self ip as " + str(self.self_ip6))

    def findChildIps(self) -> None:
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
                        print(line[6:].strip()  + " does not match BR prefix " + prefix)
                    else:
                        tmp = ipaddress.ip_address(line[6:])
                        if tmp not in self.child_ip6:
                            self.pend_queue_child_ips.add(tmp)
                            print(line[6:].strip()  + " added to child notif queue")
                        self.child_ip6.add(tmp)
                        print(line[6:].strip()  + " updated in child sensitivity list")
                except ValueError:
                    pass

            last = str(process.poll())
            try:
                last = last.rstrip()
                if last not in self.child_ip6:
                    self.pend_queue_child_ips.add(last)
                    print(last[6:].strip() + " added to child notif queue")
                print(last[6:].strip()  + " added to child sensitivity list")
                tmp = ipaddress.ip_address(last[6:])
                self.child_ip6.add(tmp)
            except ValueError:
                pass
            if last is not None:
                break

    def getChildIps(self) -> set[IPv6Address]:
        return self.child_ip6

    def dequePendChildIps(self) -> IPv6Address:
        try:
            ret = self.pend_queue_child_ips.pop()
            return ret
        except KeyError:
            return ipaddress.ip_address("::")