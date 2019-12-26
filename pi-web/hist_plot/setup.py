"""  """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"
from distutils.core import setup

version = '1.0'

setup(name='hist_plot',
      version=version,
      install_requires=['gunicorn',
                        'jinja2',
                        'flask',
                        'pandas',
                        'numpy',
                        'matplotlib'
                        ],
      description='''app to show inf history.
                 ''',
      author='Bryan Staley',
      author_email='bryan.w.staley@gmail.com',
      scripts=[],
      packages=['hist_plot'],
      )
