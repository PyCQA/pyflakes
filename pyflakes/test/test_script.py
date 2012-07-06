
"""
Tests for L{pyflakes.scripts.pyflakes}.
"""

import sys
from StringIO import StringIO

from twisted.python.filepath import FilePath
from twisted.trial.unittest import TestCase

from pyflakes.scripts.pyflakes import (
    checkPath,
    Reporter,
    )


def withStderrTo(stderr, f, *args, **kwargs):
    """
    Call C{f} with C{sys.stderr} redirected to C{stderr}.
    """
    (outer, sys.stderr) = (sys.stderr, stderr)
    try:
        return f(*args, **kwargs)
    finally:
        sys.stderr = outer


class LoggingReporter(object):

    def __init__(self, log):
        self.log = log

    def ioError(self, filename, exception):
        self.log.append(('ioError', filename, exception.args[1]))

    def problemDecodingSource(self, filename):
        self.log.append(('problemDecodingSource', filename))

    def syntaxError(self, filename, msg, lineno, offset, line):
        self.log.append(('syntaxError', filename, msg, lineno, offset, line))


class TestReporter(TestCase):
    """
    Tests for L{Reporter}.
    """

    def test_problemDecodingSource(self):
        """
        C{problemDecodingSource} reports that there was a problem decoding the
        source to the error stream.  It includes the filename that it couldn't
        decode.
        """
        err = StringIO()
        reporter = Reporter(err)
        reporter.problemDecodingSource('foo.py')
        self.assertEquals("foo.py: problem decoding source\n", err.getvalue())


    def test_syntaxError(self):
        """
        C{syntaxError} reports that there was a syntax error in the source
        file.  It reports to the error stream and includes the filename, line
        number, error message, actual line of source and a caret pointing to
        where the error is.
        """
        err = StringIO()
        reporter = Reporter(err)
        reporter.syntaxError('foo.py', 'a problem', 3, 4, 'bad line of source')
        self.assertEquals(
            ("foo.py:3: a problem\n"
             "bad line of source\n"
             "     ^\n"),
            err.getvalue())


    def test_syntaxErrorNoOffset(self):
        """
        C{syntaxError} doesn't include a caret pointing to the error if
        C{offset} is passed as C{None}.
        """
        err = StringIO()
        reporter = Reporter(err)
        reporter.syntaxError('foo.py', 'a problem', 3, None,
                             'bad line of source')
        self.assertEquals(
            ("foo.py:3: a problem\n"
             "bad line of source\n"),
            err.getvalue())


    def test_multiLineSyntaxError(self):
        """
        If there's a multi-line syntax error, then we only report the last
        line.  The offset is adjusted so that it is relative to the start of
        the last line.
        """
        err = StringIO()
        lines = [
            'bad line of source',
            'more bad lines of source',
            ]
        reporter = Reporter(err)
        reporter.syntaxError('foo.py', 'a problem', 3, len(lines[0]) + 5,
                             '\n'.join(lines))
        self.assertEquals(
            ("foo.py:3: a problem\n" +
             lines[-1] + "\n" +
             "     ^\n"),
            err.getvalue())


    def test_ioError(self):
        """
        C{ioError} reports an error reading a source file.  It only includes
        the human-readable bit of the error message, and excludes the errno.
        """
        err = StringIO()
        reporter = Reporter(err)
        exception = IOError(42, 'bar')
        try:
            raise exception
        except IOError, e:
            pass
        reporter.ioError('source.py', e)
        self.assertEquals('source.py: bar\n', err.getvalue())



class CheckTests(TestCase):
    """
    Tests for L{check} and L{checkPath} which check a file for flakes.
    """

    def makeTempFile(self, content):
        """
        Make a temporary file containing C{content} and return a path to it.
        """
        path = FilePath(self.mktemp())
        path.setContent(content)
        return path.path


    def assertHasErrors(self, path, errorList):
        """
        Assert that C{path} causes errors.

        @param path: A path to a file to check.
        @param errorList: A list of errors expected to be printed to stderr.
        """
        err = StringIO()
        count = withStderrTo(err, checkPath, path)
        self.assertEquals(
            (count, err.getvalue()), (len(errorList), ''.join(errorList)))


    def getErrors(self, path):
        log = []
        reporter = LoggingReporter(log)
        count = checkPath(path, reporter)
        return count, log


    def test_missingTrailingNewline(self):
        """
        Source which doesn't end with a newline shouldn't cause any
        exception to be raised nor an error indicator to be returned by
        L{check}.
        """
        fName = self.makeTempFile("def foo():\n\tpass\n\t")
        self.assertHasErrors(fName, [])


    def test_checkPathNonExisting(self):
        """
        L{checkPath} handles non-existing files.
        """
        count, errors = self.getErrors('extremo')
        self.assertEquals(count, 1)
        self.assertEquals(
            errors, [('ioError', 'extremo', 'No such file or directory')])


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

        sourcePath = self.makeTempFile(source)
        self.assertHasErrors(
            sourcePath, ["""\
%s:8: invalid syntax
    '''quux'''
           ^
"""
                % (sourcePath,)])


    def test_eofSyntaxError(self):
        """
        The error reported for source files which end prematurely causing a
        syntax error reflects the cause for the syntax error.
        """
        sourcePath = self.makeTempFile("def foo(")
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:1: unexpected EOF while parsing
def foo(
         ^
""" % (sourcePath,)])


    def test_nonDefaultFollowsDefaultSyntaxError(self):
        """
        Source which has a non-default argument following a default argument
        should include the line number of the syntax error.  However these
        exceptions do not include an offset.
        """
        source = """\
def foo(bar=baz, bax):
    pass
"""
        sourcePath = self.makeTempFile(source)
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:1: non-default argument follows default argument
def foo(bar=baz, bax):
""" % (sourcePath,)])


    def test_nonKeywordAfterKeywordSyntaxError(self):
        """
        Source which has a non-keyword argument after a keyword argument should
        include the line number of the syntax error.  However these exceptions
        do not include an offset.
        """
        source = """\
foo(bar=baz, bax)
"""
        sourcePath = self.makeTempFile(source)
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:1: non-keyword arg after keyword arg
foo(bar=baz, bax)
""" % (sourcePath,)])


    def test_permissionDenied(self):
        """
        If the a source file is not readable, this is reported on standard
        error.
        """
        sourcePath = FilePath(self.mktemp())
        sourcePath.setContent('')
        sourcePath.chmod(0)
        count, errors = self.getErrors(sourcePath.path)
        self.assertEquals(count, 1)
        self.assertEquals(
            errors, [('ioError', sourcePath.path, "Permission denied")])


    def test_misencodedFile(self):
        """
        If a source file contains bytes which cannot be decoded, this is
        reported on stderr.
        """
        source = u"""\
# coding: ascii
x = "\N{SNOWMAN}"
""".encode('utf-8')
        sourcePath = self.makeTempFile(source)
        self.assertHasErrors(
            sourcePath, ["%s: problem decoding source\n" % (sourcePath,)])
