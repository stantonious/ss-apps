""" PI core inference package """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# add file handler
fh = logging.FileHandler('/var/log/ss/ss.log')
fh.setLevel(logging.DEBUG)
