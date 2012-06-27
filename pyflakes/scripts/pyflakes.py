
"""
Implementation of the command-line I{pyflakes} tool.
"""

import sys
import os
import _ast

checker = __import__('pyflakes.checker').checker


class Reporter(object):

    def __init__(self, stdout=None, stderr=None):
        if stdout is None:
            stdout = sys.stdout
        self._stdout = stdout
        if stderr is None:
            stderr = sys.stderr
        self._stderr = stderr

    def _print_error(self, msg):
        self._stderr.write(msg)
        self._stderr.write('\n')

    def ioError(self, filename, msg):
        self._print_error("%s: %s" % (filename, msg.args[1]))

    def problemDecodingSource(self, filename):
        self._print_error("%s: problem decoding source\n" % (filename,))

    def syntaxError(self, filename, msg, lineno, offset, line):
        self._print_error('%s:%d: %s' % (filename, lineno, msg))
        self._print_error(line)
        if offset is not None:
            self._print_error(" " * offset, "^")

    def flake(self, warning):
        self._stdout.write(warning)
        self._stdout.write('\n')


def check(codeString, filename, reporter=None):
    """
    Check the Python source given by C{codeString} for flakes.

    @param codeString: The Python source to check.
    @type codeString: C{str}

    @param filename: The name of the file the source came from, used to report
        errors.
    @type filename: C{str}

    @return: The number of warnings emitted.
    @rtype: C{int}
    """
    if reporter is None:
        reporter = Reporter()
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
            reporter.problem_decoding_source(filename)
        else:
            line = text.splitlines()[-1]
            if offset is not None:
                offset = offset - (len(text) - len(line))
            reporter.syntax_error(filename, msg, lineno, offset, line)
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

    @return: the number of warnings printed
    """
    try:
        return check(file(filename, 'U').read() + '\n', filename, reporter)
    except IOError, msg:
        reporter.ioError(filename, msg)
        return 1


def checkRecursive(paths, reporter=None):
    """
    Check the given files and look recursively under any directories, looking
    for Python files and checking them, printing out any warnings detected.

    @param paths: A list of file and directory names.
    @return: the number of warnings printed
    """
    warnings = 0
    for path in paths:
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    if filename.endswith('.py'):
                        warnings += checkPath(os.path.join(dirpath, filename),
                                              reporter)
        else:
            warnings += checkPath(path, reporter)
    return warnings


def main():
    warnings = 0
    args = sys.argv[1:]
    if args:
        warnings += checkRecursive(args)
    else:
        warnings += check(sys.stdin.read(), '<stdin>')

    raise SystemExit(warnings > 0)
