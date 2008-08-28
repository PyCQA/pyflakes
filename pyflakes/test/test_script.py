
"""
Tests for L{pyflakes.scripts.pyflakes}.
"""

from twisted.python.filepath import FilePath
from twisted.trial.unittest import TestCase

from pyflakes.scripts.pyflakes import checkPath

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
