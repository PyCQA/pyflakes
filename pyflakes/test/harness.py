
import textwrap
import _ast

import unittest2

from pyflakes import checker


class Test(unittest2.TestCase):

    def flakes(self, input, *expectedOutputs, **kw):
        ast = compile(textwrap.dedent(input), "<test>", "exec",
                      _ast.PyCF_ONLY_AST)
        w = checker.Checker(ast, **kw)
        outputs = [type(o) for o in w.messages]
        expectedOutputs = list(expectedOutputs)
        outputs.sort(key=lambda t: t.__name__)
        expectedOutputs.sort(key=lambda t: t.__name__)
        self.assertEqual(outputs, expectedOutputs, '''\
for input:
%s
expected outputs:
%s
but got:
%s''' % (input, repr(expectedOutputs), '\n'.join([str(o) for o in w.messages])))
        return w
