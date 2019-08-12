"""
Provide the Reporter class.
"""

import re
import sys


class Reporter(object):
    """
    Formats the results of pyflakes checks to users.
    """

    def __init__(self, warningStream, errorStream):
        """
        Construct a L{Reporter}.

        @param warningStream: A file-like object where warnings will be
            written to.  The stream's C{write} method must accept unicode.
            C{sys.stdout} is a good value.
        @param errorStream: A file-like object where error output will be
            written to.  The stream's C{write} method must accept unicode.
            C{sys.stderr} is a good value.
        """
        self._stdout = warningStream
        self._stderr = errorStream

    def unexpectedError(self, filename, msg):
        """
        An unexpected error occurred trying to process C{filename}.

        @param filename: The path to a file that we could not process.
        @ptype filename: C{unicode}
        @param msg: A message explaining the problem.
        @ptype msg: C{unicode}
        """
        self._stderr.write("%s: %s\n" % (filename, msg))

    def syntaxError(self, filename, msg, lineno, offset, text):
        """
        There was a syntax error in C{filename}.

        @param filename: The path to the file with the syntax error.
        @ptype filename: C{unicode}
        @param msg: An explanation of the syntax error.
        @ptype msg: C{unicode}
        @param lineno: The line number where the syntax error occurred.
        @ptype lineno: C{int}
        @param offset: The column on which the syntax error occurred, or None.
        @ptype offset: C{int}
        @param text: The source code containing the syntax error.
        @ptype text: C{unicode}
        """
        line = text.splitlines()[-1]
        if offset is not None:
            if sys.version_info < (3, 8):
                offset = offset - (len(text) - len(line)) + 1
            self._stderr.write('%s:%d:%d: %s\n' %
                               (filename, lineno, offset, msg))
        else:
            self._stderr.write('%s:%d: %s\n' % (filename, lineno, msg))
        self._stderr.write(line)
        self._stderr.write('\n')
        if offset is not None:
            self._stderr.write(re.sub(r'\S', ' ', line[:offset - 1]) +
                               "^\n")

    def flake(self, message):
        """
        pyflakes found something wrong with the code.

        @param: A L{pyflakes.messages.Message}.
        """
        self._stdout.write(str(message))
        self._stdout.write('\n')


class ListReporter(object):
    """Simple reporter class that logs all entries to list of
    dictionaries with consistent structure."""

    def __init__(self):
        """
        Initialize empty list for entries.
        """
        self.entries = []

    def unexpectedError(self, filename, msg):
        self.entries.append({"message_class": "error",
                             "message_type": "unexpected_error",
                             "filename": filename,
                             "lineno": None,
                             "offset": None,
                             "message": msg,
                             "source": None, })

    def syntaxError(self, filename, msg, lineno, offset, text):
        self.entries.append({"message_class": "error",
                             "message_type": "syntax_error",
                             "filename": filename,
                             "lineno": lineno,
                             "offset": offset,
                             "message": msg,
                             "source": text, })

    def flake(self, message):
        self.entries.append({"message_class": "warning",
                             "message_type": "flake_warning",
                             "filename": message.filename,
                             "lineno": message.lineno,
                             "offset": message.col,
                             "message": message.message % message.message_args,
                             "source": None, })


def _makeDefaultReporter():
    """
    Make a reporter that can be used when no reporter is specified.
    """
    return Reporter(sys.stdout, sys.stderr)
