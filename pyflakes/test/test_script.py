
"""
Tests for L{pyflakes.scripts.pyflakes}.
"""

import sys
from StringIO import StringIO

from twisted.python.filepath import FilePath
from twisted.trial.unittest import TestCase

from pyflakes.scripts.pyflakes import checkPath

def withStderrTo(stderr, f):
    """
    Call C{f} with C{sys.stderr} redirected to C{stderr}.
    """
    (outer, sys.stderr) = (sys.stderr, stderr)
    try:
        return f()
    finally:
        sys.stderr = outer



class CheckTests(TestCase):
    """
    Tests for L{check} and L{checkPath} which check a file for flakes.
    """
    def test_missingTrailingNewline(self):
        """
        Source which doesn't end with a newline shouldn't cause any
        exception to be raised nor an error indicator to be returned by
        L{check}.
        """
        fName = self.mktemp()
        FilePath(fName).setContent("def foo():\n\tpass\n\t")
        self.assertFalse(checkPath(fName))


    def test_checkPathNonExisting(self):
        """
        L{checkPath} handles non-existing files.
        """
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath('extremo'))
        self.assertEquals(err.getvalue(), 'extremo: no such file\n')
        self.assertEquals(count, 1)


    def test_multilineSyntaxError(self):
        """
        Source which includes a syntax error which results in the raised
        L{SyntaxError.text} containing multiple lines of source are reported
        with only the last line of that source.
        """
        source = """\
def foo():
    '''

def bar():
    pass

def baz():
    '''quux'''
"""

        # Sanity check - SyntaxError.text should be multiple lines, if it
        # isn't, something this test was unprepared for has happened.
        def evaluate(source):
            exec source
        exc = self.assertRaises(SyntaxError, evaluate, source)
        self.assertTrue(exc.text.count('\n') > 1)

        sourcePath = FilePath(self.mktemp())
        sourcePath.setContent(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath.path))
        self.assertEqual(count, 1)

        self.assertEqual(
            err.getvalue(),
            """\
%s:8: invalid syntax
    '''quux'''
           ^
""" % (sourcePath.path,))


    def test_eofSyntaxError(self):
        """
        The error reported for source files which end prematurely causing a
        syntax error reflects the cause for the syntax error.
        """
        source = "def foo("
        sourcePath = FilePath(self.mktemp())
        sourcePath.setContent(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath.path))
        self.assertEqual(count, 1)
        self.assertEqual(
            err.getvalue(),
            """\
%s:1: unexpected EOF while parsing
def foo(
         ^
""" % (sourcePath.path,))

