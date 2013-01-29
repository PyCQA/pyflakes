#!/usr/bin/env python
# Copyright 2005-2011 Divmod, Inc.
# Copyright 2013 Florent Xicluna.  See LICENSE file for details
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
    extra = {'scripts': ["bin/pyflakes"]}
else:
    if sys.version_info < (3,):
        extra = {'tests_require': ['unittest2'],
                 'test_suite': 'unittest2.collector'}
    else:
        extra = {'tests_require': ['unittest2py3k'],
                 'test_suite': 'unittest2.collector.collector'}
    extra['entry_points'] = {
        'console_scripts': ['pyflakes = pyflakes.api:main'],
    }

setup(
    name="pyflakes",
    license="MIT",
    version="0.6.1",
    description="passive checker of Python programs",
    author="Phil Frost",
    author_email="indigo@bitglue.com",
    maintainer="Florent Xicluna",
    maintainer_email="pyflakes-dev@lists.launchpad.net",
    url="https://launchpad.net/pyflakes",
    packages=["pyflakes", "pyflakes.scripts", "pyflakes.test"],
    long_description="""Pyflakes is program to analyze Python programs and detect various errors. It
works by parsing the source file, not importing it, so it is safe to use on
modules with side effects. It's also much faster.""",
    classifiers=[
        "Development Status :: 6 - Mature",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development",
        "Topic :: Utilities",
    ],
    **extra)
