'''
Created on May 31, 2019

@author: bstaley
'''
from distutils.core import setup

version = '1.0'

setup(name='rmq_app',
      version=version,
      install_requires=[
      ],
      description='''ss inference engine gui.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=['run_rmq_app.sh'],
      packages=['rmq_app'],
      )
