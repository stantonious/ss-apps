""" pi-app setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2021"
__credits__ = []
__license__ = "GPL"

from distutils.core import setup

version = '1.0'

setup(name='ss_ttgo',
      version=version,
      install_requires=[
          'numpy',
          'pika',
          'bleak',
      ],
      description='''Applications to control an lilygo wearable watch (v1)
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=[ 'ttgo-controller.py',
                'ttgo-labeler.py',
                'ttgo-sampler.py',
                'ttgo-class-train.py',
                'ttgo-inf.py'],
      packages=[],
      )
