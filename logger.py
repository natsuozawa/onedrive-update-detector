import logging
import os

logger = logging.getLogger('oud')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)
logger.addHandler(ch)
