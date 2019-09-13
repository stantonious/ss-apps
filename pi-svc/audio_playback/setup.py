'''
Created on May 31, 2019

@author: bstaley
'''
from distutils.core import setup

version = '1.0'

setup(name='playback_app',
      version=version,
      install_requires=['gunicorn',
                        'flask'

                        ],
      description='''ss audio retrieval app.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=['run_audio_playback.sh',
               'playback.py'],
      packages=[],

      )
