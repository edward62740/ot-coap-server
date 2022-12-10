import ipaddress
import subprocess
import asyncio
from ipaddress import IPv6Address
from typing import Set, Type


class OtManager:
    child_ip6 = set[ipaddress.IPv6Address]
    self_ip6 = ipaddress.IPv6Address

    def __init__(self, self_ip: Type[IPv6Address]):
        if Type[self_ip] is not IPv6Address:
            raise ValueError
        self.self_ip6 = self_ip

    def textToChildIps(self, text: str) -> None:
        lines = text.strip().splitlines()
        for line in lines:
            try:
                print(line[6:])
                tmp = ipaddress.ip_address(line[6:])
                self.child_ip6.add(tmp)
            except ValueError:
                pass

    def getChildIps(self) -> Type[set[IPv6Address]]:
        return self.child_ip6
