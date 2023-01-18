# ot-CoAP Server for [ot-IPR](https://github.com/edward62740/ot-IPR)


This is a python script for ot-IPR to provide CoAP server function.
Running main.py will do the following tasks:
    
      1. Start a CoAP server on port 5683, and bind to wpan0 i/f on mesh local address
      2. Start a task to poll ot-ctl every POLL_NEW_CHILDREN_INTERVAL_S to check if there is any new child
      3. Start a task to post data to influxDB
      4. Start a task to manage existing children and store their data in a OtDevice class
      5. Call user_handler_callback whenever valid CoAP message is received, for easily customizable user defined functions

