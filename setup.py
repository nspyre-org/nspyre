#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs

from setuptools import setup


def read(filename):
    return codecs.open(filename, encoding='utf-8').read()


long_description = '\n\n'.join([read('LICENSE'),
                                read('README.md'),
                                read('AUTHORS')])

__doc__ = long_description

setup(name='nspyre',
      version='0.3.0rc1',
      packages=['nspyre', ],
      license='MIT',
      description='Networked Scientific Python Research Environment',
      long_description=long_description,
      long_description_content_type="text/markdown",
      keywords='measurement control instrumentation science',
      author='Alexandre Bourassa',
      author_email='abourassa@uchicago.edu',
      url='https://github.com/AlexBourassa/nspyre',
      install_requires=[
          'numpy>=1.16.4',
          'pymongo>=3.9.0',
          'pandas>=0.25.2',
          'pyqtgraph>=0.11.0',
          'qscintilla>=2.11.0',
          'pyyaml>=5.1.2',
          'scipy>=1.2.1',
          'tqdm>=4.32.2',
          'parse>=1.16.0',
          'pint>=0.14',
          'waiting>=1.4.1',
          'rpyc>=4.1.5',
          'lantzdev>=0.5',
      ],
      platforms='any',
      entry_points={
          'console_scripts': ['nspyre = nspyre.gui.main:main']
      },
      classifiers=[
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: MIT License",
      ],
      )
