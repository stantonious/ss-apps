""" Inference App setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

from distutils.core import setup

version = '1.0'

setup(name='inf_app',
      version=version,
      install_requires=['ss_core',
                        'psycopg2',
                        ],
      description='''ss inference engine.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=['classifier.py',
               'yamnet_classifier.py',
               'inf_recorder.py',
               'mel_recorder.py'],
      packages=[],
      )
