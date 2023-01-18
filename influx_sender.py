import asyncio
from datetime import datetime
import logging
from influxdb_client import Point, WritePrecision
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

from ot_manager import OtManager, OtDeviceType


async def influx_task(ot_mgr: OtManager):
    """Task to periodically send data to influxdb."""
    bucket = ""
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
                alive = ot_mgr.get_child_ips()[ip].last_seen > datetime.now().timestamp() - 30
                if ot_mgr.get_child_ips()[ip].device_type == OtDeviceType.RADAR:
                    point = (
                        Point("ot-ipr")
                        .tag("ip", ip)
                        .field("radar_dist", float(ot_mgr.get_child_ips()[ip].radar_dist))
                        .field("opt_lux", int(ot_mgr.get_child_ips()[ip].opt_lux))
                        .field("radar_conf", float(ot_mgr.get_child_ips()[ip].radar_conf))
                        .field("radar_flag", bool(ot_mgr.get_child_ips()[ip].radar_flag))
                        .field("supply_vdd", int(ot_mgr.get_child_ips()[ip].vdd))
                        .field("rssi", int(ot_mgr.get_child_ips()[ip].rssi))
                        .field("alive", bool(alive))
                        .field("alive_ctr", int(ot_mgr.get_child_ips()[ip].ctr))
                        .time(datetime.utcnow(), WritePrecision.MS)
                    )
                    # Write the data point to the database
                    try:
                        await client.write_api().write(bucket, org, point)
                    except (OSError, TimeoutError):
                        logging.error("Could not connect to influxdb")
                    except Exception as err:
                        logging.error("Could not write to influxdb")
                        logging.error(err)
