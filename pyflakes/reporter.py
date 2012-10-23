# (c) 2005-2012 Divmod, Inc.
# See LICENSE file for details

import sys


class Reporter(object):
    """
    Formats the results of pyflakes checks to users.
    """

    def __init__(self, warningStream, errorStream):
        """
        Construct a L{Reporter}.

        @param warningStream: A file-like object where warnings will be
            written to.  C{sys.stdout} is a good value.
        @param errorStream: A file-like object where error output will be
            written to.  C{sys.stderr} is a good value.
        """
        self._stdout = warningStream
        self._stderr = errorStream


    def unexpectedError(self, filename, msg):
        """
        An unexpected error occurred trying to process C{filename}.

        @param filename: The path to a file that we could not process.
        @ptype filename: text
        @param msg: A message explaining the problem.
        @ptype msg: text
        """
        self._stderr.write("%s: %s\n" % (filename, msg))


    def ioError(self, filename, msg):
        """
        There was an C{IOError} while reading C{filename}.
        """
        self.unexpectedError(filename, msg.args[1])


    def problemDecodingSource(self, filename):
        """
        There was a problem decoding the source code in C{filename}.
        """
        self.unexpectedError(filename, 'problem decoding source')


    def syntaxError(self, filename, msg, lineno, offset, text):
        """
        There was a syntax errror in C{filename}.

        @param filename: The path to the file with the syntax error.
        @param msg: An explanation of the syntax error.
        @param lineno: The line number where the syntax error occurred.
        @param offset: The column on which the syntax error occurred.
        @param text: The source code containing the syntax error.
        """
        line = text.splitlines()[-1]
        if offset is not None:
            offset = offset - (len(text) - len(line))
        self._stderr.write('%s:%d: %s\n' % (filename, lineno, msg))
        self._stderr.write(line)
        self._stderr.write('\n')
        if offset is not None:
            self._stderr.write(" " * (offset + 1) + "^\n")


    def flake(self, message):
        """
        pyflakes found something wrong with the code.

        @param: A L{pyflakes.messages.Message}.
        """
        self._stdout.write(str(message))
        self._stdout.write('\n')



def _makeDefaultReporter():
    """
    Make a reporter that can be used when no reporter is specified.
    """
    return Reporter(sys.stdout, sys.stderr)
