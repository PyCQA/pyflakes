import ast
import textwrap
import unittest

from pyflakes import checker

__all__ = ['TestCase', 'skip', 'skipIf']

skip = unittest.skip
skipIf = unittest.skipIf


class TestCase(unittest.TestCase):

    withDoctest = False

    def flakes(self, input, *expectedOutputs, is_segment=False, **kw):
        tree = ast.parse(textwrap.dedent(input))
        if is_segment:
            tree = tree.body[0]
        w = checker.Checker(tree, withDoctest=self.withDoctest, **kw)
        outputs = [type(o) for o in w.messages]
        expected = sorted(expectedOutputs, key=lambda t: t.__name__)
        outputs.sort(key=lambda t: t.__name__)
        self.assertEqual(outputs, expected, '''\
for input:
{}
expected outputs:
{!r}
but got:
{}'''.format(input, expected, '\n'.join([str(o) for o in w.messages])))
        return w
