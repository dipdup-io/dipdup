import logging
from os import environ as env

if env.get('DEBUG'):
    logging.basicConfig(level=logging.DEBUG)
