""" pi-app setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

from distutils.core import setup

version = '1.0'

setup(name='ss_status_apps',
      version=version,
      install_requires=[
      ],
      description='''status apps.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=['heartbeat.py'],
      packages=[]
      )
