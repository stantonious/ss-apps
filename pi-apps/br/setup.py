""" pi-app setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

from distutils.core import setup

version = '1.0'

setup(name='ss_br_apps',
      version=version,
      install_requires=[
          'business_rules',
          'numpy',
          'pika',
          'requests',
          'spidev',
          'colour'
      ],
      description='''br apps.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=['audio_recorder.py',
               'backoff.py',
               'leds.py',
               'notification.py',
               'embedding_recorder.py'],
      packages=['app_utils']
      )
