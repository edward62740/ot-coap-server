import asyncio
from datetime import datetime
import logging
from influxdb_client import Point, WritePrecision
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

from ot_manager import OtManager




async def influx_task(ot_mgr: OtManager):
    """ Task to periodically send data to influxdb. """
    bucket = "ipr"
    org = ""
    token = ""
    # Store the URL of your InfluxDB instance
    url = ""
    async with InfluxDBClientAsync(url=url, token=token, org=org) as client:
        # set bucket
        while True:
            await asyncio.sleep(15)
            logging.info("Sent data to influxdb")
            # Create a data point for the OtDevice instance, and send it to the
            # InfluxDB server

            for ip in ot_mgr.get_child_ips():
                alive = ot_mgr.get_child_ips(
                )[ip].last_seen > datetime.now().timestamp() - 30
                point = Point("ot-ipr") .tag(
                    "ip",
                    ip) .field(
                    "detected_dist",
                    ot_mgr.get_child_ips()[ip].det_dist) .field(
                    "lux",
                    ot_mgr.get_child_ips()[ip].det_lux) .field(
                    "detected_conf",
                    ot_mgr.get_child_ips()[ip].det_conf) .field(
                    "detected_flag",
                    ot_mgr.get_child_ips()[ip].det_flag) .field(
                        "vdd",
                        ot_mgr.get_child_ips()[ip].det_vdd) .field(
                            "rssi",
                            ot_mgr.get_child_ips()[ip].det_rssi) .field(
                                "alive",
                                alive) .field(
                                    "ctr",
                                    ot_mgr.get_child_ips()[ip].ctr) .time(
                                        datetime.utcnow(),
                    WritePrecision.MS)

                # Write the data point to the database
                try:
                    await client.write_api().write(bucket, org, point)
                except (OSError, TimeoutError):
                    logging.error("Could not connect to influxdb")
                except Exception as err:
                    logging.error("Could not write to influxdb")
                    logging.error(err)

