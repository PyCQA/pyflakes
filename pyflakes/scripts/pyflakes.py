
"""
Implementation of the command-line I{pyflakes} tool.
"""

import sys
import os
import _ast

checker = __import__('pyflakes.checker').checker


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


    def ioError(self, filename, msg):
        """
        There was an C{IOError} while reading C{filename}.
        """
        self._stderr.write("%s: %s\n" % (filename, msg.args[1]))


    def problemDecodingSource(self, filename):
        """
        There was a problem decoding the source code in C{filename}.
        """
        self._stderr.write(filename)
        self._stderr.write(': problem decoding source\n')


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


def check(codeString, filename, reporter=None):
    """
    Check the Python source given by C{codeString} for flakes.

    @param codeString: The Python source to check.
    @type codeString: C{str}

    @param filename: The name of the file the source came from, used to report
        errors.
    @type filename: C{str}

    @param reporter: A L{Reporter} instance, where errors and warnings will be
        reported.

    @return: The number of warnings emitted.
    @rtype: C{int}
    """
    if reporter is None:
        reporter = Reporter(None, sys.stderr)
    # First, compile into an AST and handle syntax errors.
    try:
        tree = compile(codeString, filename, "exec", _ast.PyCF_ONLY_AST)
    except SyntaxError, value:
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        # If there's an encoding problem with the file, the text is None.
        if text is None:
            # Avoid using msg, since for the only known case, it contains a
            # bogus message that claims the encoding the file declared was
            # unknown.
            reporter.problemDecodingSource(filename)
        else:
            reporter.syntaxError(filename, msg, lineno, offset, text)
        return 1
    else:
        # Okay, it's syntactically valid.  Now check it.
        w = checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        for warning in w.messages:
            reporter.flake(warning)
        return len(w.messages)


def checkPath(filename, reporter=None):
    """
    Check the given path, printing out any warnings detected.

    @param reporter: A L{Reporter} instance, where errors and warnings will be
        reported.

    @return: the number of warnings printed
    """
    if reporter is None:
        reporter = Reporter(None, sys.stderr)
    try:
        return check(file(filename, 'U').read() + '\n', filename, reporter)
    except IOError, msg:
        reporter.ioError(filename, msg)
        return 1



def iterSourceCode(paths):
    """
    Iterate over all Python source files in C{paths}.

    @param paths: A list of paths.  Directories will be recursed into and
        any .py files found will be yielded.  Any non-directories will be
        yielded as-is.
    """
    for path in paths:
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    if filename.endswith('.py'):
                        yield os.path.join(dirpath, filename)
        else:
            yield path



def checkRecursive(paths, reporter):
    """
    Recursively check all source files in C{paths}.

    @param paths: A list of paths to Python source files and directories
        containing Python source files.
    @param reporter: A L{Reporter} where all of the warnings and errors
        will be reported to.
    @return: The number of warnings found.
    """
    warnings = 0
    for sourcePath in iterSourceCode(paths):
        warnings += checkPath(sourcePath, reporter)
    return warnings



def main():
    args = sys.argv[1:]
    reporter = Reporter(sys.stdout, sys.stderr)
    if args:
        warnings = checkRecursive(args, reporter)
    else:
        warnings = check(sys.stdin.read(), '<stdin>', reporter)
    raise SystemExit(warnings > 0)
