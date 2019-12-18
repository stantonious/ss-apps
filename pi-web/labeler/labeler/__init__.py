""" Labeler package """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"
from flask import Flask
import logging
import sys
app = Flask(__name__)

from . import routes