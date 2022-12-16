import asyncio
from datetime import datetime

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client import influxdb_client

from ot_manager import OtManager

import logging

async def influx_task(ot_mgr: OtManager):
    """ Task to periodically send data to influxdb. """
    # Create a connection to the InfluxDB server
    bucket = ""
    org = ""
    token = ""
    # Store the URL of your InfluxDB instance
    url = ""
    client = influxdb_client.InfluxDBClient(
        url=url,
        token=token,
        org=org
    )
    # set bucket
    while True:
        await asyncio.sleep(15)
        logging.info("Sent data to influxdb")
        # Create a data point for the OtDevice instance, and send it to the InfluxDB server

        for ip in ot_mgr.get_child_ips():
            alive = ot_mgr.get_child_ips()[ip].last_seen > datetime.now().timestamp() - 30
            point = Point("ot-ipr") \
                .tag("ip", ip) \
                .field("detected_dist", ot_mgr.get_child_ips()[ip].det_dist) \
                .field("lux", ot_mgr.get_child_ips()[ip].det_lux) \
                .field("detected_conf", ot_mgr.get_child_ips()[ip].det_conf) \
                .field("detected_flag", ot_mgr.get_child_ips()[ip].det_flag) \
                .field("vdd", ot_mgr.get_child_ips()[ip].det_vdd) \
                .field("alive", alive) \
                .time(datetime.utcnow(), WritePrecision.MS)

            # Write the data point to the database
            logging.info(str(point))
            client.write_api().write(bucket, org, point)