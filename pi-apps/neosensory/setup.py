""" pi-app setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2020"
__credits__ = []
__license__ = "GPL"

from distutils.core import setup

version = '1.0'

setup(name='ss_neosensory',
      version=version,
      install_requires=[
          'numpy',
          'pika',
          'bleak',
          'neosensory_python',
      ],
      description='''Applications to control an neosensory buzz 
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=[ 'buzz.py',],
      packages=[],
      )
