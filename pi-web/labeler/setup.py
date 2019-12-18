""" PI app inference GUI setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"
from distutils.core import setup

version = '1.0'

setup(name='inf_gui',
      version=version,
      install_requires=['bokeh',
                        'pika',
                        'numpy',
                        ],
      description='''ss labeler gui.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=[],
      packages=['labeler'],
      )
