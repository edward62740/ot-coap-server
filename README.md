# ot-CoAP Server for [ot-IPR](https://github.com/edward62740/ot-IPR)


This is a python script for ot-IPR/HS to provide CoAP server function.

Implements a CoAP server with DNS-SD capabilities, automatic device management/recovery and InfluxDB integration. Load tested to 25 x SED.

CoAP messages are sent in CSV format, where the first two entries must be the OtDeviceType, and hex string EUI64.
Any other entries are device-specific and can be created using a class inherited from OtDevice.

Example of payload: ```0,4ED909C55E57B9F6,448328,91281,839192839,10000028911,1,1```


Running main.py will do the following tasks:
    
1. Start a CoAP server on port 5683, and bind to wpan0 i/f on mesh local address. Params like ACK_TIMEOUT should be changed based on requirements or repeated ack failures may cause issues.
2. Start OtManager, pass an optional argument "1" to the constructor to select RFC6763 service discovery task, else will poll ot-ctl for children by default.
3. Start a task to poll ot-ctl OR handle a queue of discovered IPs (depending on 2.) every POLL_NEW_CHILDREN_INTERVAL_S to check if there is any new child, if so, passing a unique uri path to the new child.
4. Start a task to monitor existing children, reattempting to connect to the child if it is not connected by sending its dedicated resource path every OT_DEVICE_CHILD_TIMEOUT_S.
    After OT_DEVICE_TIMEOUT_CYCLES, the child will be removed from the list. The child timeout value is tied to OPENTHREAD_CONFIG_SUPERVISION_CHECK_TIMEOUT.
5. Start a task to post data to influxDB.
6. Calls user_handler_callback whenever valid CoAP message is received, for easily customizable user defined functions. It is up to the user to load main_task (in main.py) 
if there is any user defined function that needs to be called periodically.

