""" PI core setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

from distutils.core import setup

version = '1.0'

setup(name='ss_core',
      version=version,
      install_requires=['scipy'
                        ],
      description='''ss infrastructure.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=[],
      packages=[
          'inference',
          'utils',
          'vggish'],
      )
