
"""
Implementation of the command-line I{pyflakes} tool.
"""

import compiler, sys
import os

checker = __import__('pyflakes.checker').checker

def check(codeString, filename):
    # Since compiler.parse does not reliably report syntax errors, use the
    # built in compiler first to detect those.
    try:
        compile(codeString, filename, "exec")
    except (SyntaxError, IndentationError), value:
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        line = text.splitlines()[-1]

        if offset is not None:
            offset = offset - (len(text) - len(line))

        print >> sys.stderr, '%s:%d: %s' % (filename, lineno, msg)
        print >> sys.stderr, line

        if offset is not None:
            print >> sys.stderr, " " * offset, "^"

        return 1
    else:
        # Okay, it's syntactically valid.  Now parse it into an ast and check
        # it.
        tree = compiler.parse(codeString)
        w = checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        for warning in w.messages:
            print warning
        return len(w.messages)


def checkPath(filename):
    """
    Check the given path, printing out any warnings detected.

    @return: the number of warnings printed
    """
    if os.path.exists(filename):
        return check(file(filename, 'U').read() + '\n', filename)
    else:
        print >> sys.stderr, '%s: no such file' % (filename,)
        return 1

def main():
    warnings = 0
    args = sys.argv[1:]
    if args:
        for arg in args:
            if os.path.isdir(arg):
                for dirpath, dirnames, filenames in os.walk(arg):
                    for filename in filenames:
                        if filename.endswith('.py'):
                            warnings += checkPath(os.path.join(dirpath, filename))
            else:
                warnings += checkPath(arg)
    else:
        warnings += check(sys.stdin.read(), '<stdin>')

    raise SystemExit(warnings > 0)
