'''
Created on May 31, 2019

@author: bstaley
'''
from distutils.core import setup

version = '1.0'

setup(name='ss_core',
      version=version,
      install_requires=[
      ],
      description='''ss infrastructure.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=[],
      packages=[
          'inference',
          'utils'],
      )
