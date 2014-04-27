#!/usr/bin/env python

from setuptools import setup

setup(name='socketproxy',
      version=0.1,
      description='Proxy TCP connections with stream manipulation',
      author='Nick Tzaperas',
      author_email='nick@nijotz.com',
      url='http://github.com/nijotz/socketproxy',
      packages=['socketproxy'],
      entry_points = {
        'console_scripts': ['socketproxy = socketproxy:main',]
      },
      test_suite='nose.collector',
      tests_require=['nose', 'scripttest'],
)
