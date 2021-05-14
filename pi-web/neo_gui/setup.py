""" PI app inference GUI setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"
from distutils.core import setup

version = '1.0'

setup(name='neo_gui',
      version=version,
      install_requires=['bokeh',
                        'pika',
                        'numpy',
                        ],
      description='''ss neo intensity gui.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=['run_neo_gui.sh'],
      packages=['neo_gui'],
      )
