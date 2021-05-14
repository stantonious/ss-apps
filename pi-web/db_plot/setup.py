""" PI app db GUI setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"
from distutils.core import setup

version = '1.0'

setup(name='db_plot',
      version=version,
      install_requires=['bokeh',
                        'numpy',
                        ],
      description='''ss db inference gui.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=['run_db_plot.sh'],
      packages=['db_plot'],
      )
