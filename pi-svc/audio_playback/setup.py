""" PI app services setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

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
