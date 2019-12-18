""" PI app inference GUI setup """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"
from distutils.core import setup

version = '1.0'

setup(name='labeler',
      version=version,
      install_requires=['gunicorn',
                        'jinja2',
                        'flask',
                        'pandas',
                        'numpy',
                        ],
      description='''ss labeler gui.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=[],
      packages=['labeler'],
      package_data['labeler','templates/*']
      )
