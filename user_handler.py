import logging
from ipaddress import IPv6Address


from ot_manager import OtDeviceType


def user_handler_init():
    """ This function is called when the user handler is loaded. """
    logging.info("User handler loaded")
    # Add your code here


def user_handler_callback(src: IPv6Address, payload: str):
    """ This function is called when resource_handler receives something """
    logging.info("User handler callback called")
    # application-specific trigger functions
