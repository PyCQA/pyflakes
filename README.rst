========
Pyflakes
========

A simple program which checks Python source files for errors.

Pyflakes analyzes programs and detects various errors.  It works by
parsing the source file, not importing it, so it is safe to use on
modules with side effects.  It's also much faster.

It is `available on PyPI <https://pypi.python.org/pypi/pyflakes>`_
and it supports all active versions of Python from 2.5 to 3.4.



Installation
------------

It can be installed with::

  $ pip install --upgrade pyflakes


Useful tips:

* Be sure to install it for a version of Python which is compatible
  with your codebase: for Python 2, ``pip2 install pyflakes`` and for
  Python3, ``pip3 install pyflakes``.

* You can also invoke Pyflakes with ``python3 -m pyflakes .`` or
  ``python2 -m pyflakes .`` if you have it installed for both versions.

* If you require more options and more flexibility, you could give a
  look to `Flake8 <https://flake8.readthedocs.org/>`_ too.


Mailing-list
------------

Share your feedback and ideas: `subscribe to the mailing-list
<https://mail.python.org/mailman/listinfo/code-quality>`_


.. image:: https://api.travis-ci.org/pyflakes/pyflakes.png
   :target: https://travis-ci.org/pyflakes/pyflakes
   :alt: Build status

.. image:: https://pypip.in/wheel/pyflakes/badge.png
   :target: https://pypi.python.org/pypi/pyflakes
   :alt: Wheel Status
