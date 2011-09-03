#!/usr/bin/python
# Copyright 2005-2011 Divmod, Inc.  See LICENSE file for details

from distutils.core import setup

setup(
    name="pyflakes",
    license="MIT",
    version="0.5.0",
    description="passive checker of Python programs",
    author="Phil Frost",
    author_email="indigo@bitglue.com",
    maintainer="Divmod developers",
    maintainer_email="divmod-dev@lists.launchpad.net",
    url="https://launchpad.net/pyflakes",
    packages=["pyflakes", "pyflakes.scripts", "pyflakes.test"],
    scripts=["bin/pyflakes"],
    long_description="""Pyflakes is program to analyze Python programs and detect various errors. It
works by parsing the source file, not importing it, so it is safe to use on
modules with side effects. It's also much faster.""",
    classifiers=[
        "Development Status :: 6 - Mature",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Topic :: Software Development",
        "Topic :: Utilities",
        ])
