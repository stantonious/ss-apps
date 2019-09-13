'''
Created on May 31, 2019

@author: bstaley
'''
from distutils.core import setup

version = '1.0'

setup(name='inf_gui',
      version=version,
      install_requires=['bokeh',
                        'pika',
                        'numpy',

                        ],
      description='''ss inference engine gui.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=['run_inf_gui.sh'],
      packages=['inf_gui'],
      )
