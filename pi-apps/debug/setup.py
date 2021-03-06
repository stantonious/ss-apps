""" pi-app debug apps setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

from distutils.core import setup

version = '1.0'

setup(name='ss_debug_apps',
      version=version,
      install_requires=[
          'numpy',
          'pika',
      ],
      description='''debug apps.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=['inf_dump.py'],
      packages=[]
      )
