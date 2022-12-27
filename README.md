# ot-CoAP Server for [ot-IPR](https://github.com/edward62740/ot-IPR)

This python script binds aiocoap server to wpan0 i/f, listens on mesh local address, sets up a resource for each child node, then runs these tasks:
- Regularly polls ot-ctl for its child ips, and updates internally if there are any changes,
- Inform new children if they are found during polling, or attempt to reconnect with children if no communication,
- Update all received child data to InfluxDB (optional)

