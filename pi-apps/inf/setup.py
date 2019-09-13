'''
Created on May 31, 2019

@author: bstaley
'''
from distutils.core import setup

version = '1.0'

setup(name='inf_app',
      version=version,
      install_requires=['ss_core',
                        ],
      description='''ss inference engine.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=['classifier.py'],
      packages=[],
      )
