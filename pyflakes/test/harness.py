import ast
import textwrap
import unittest

from pyflakes import checker

__all__ = ['TestCase', 'skip', 'skipIf']

skip = unittest.skip
skipIf = unittest.skipIf


class TestCase(unittest.TestCase):

    withDoctest = False

    def pythonException(self, input, *expectedOutputs, **kw):
        try:
            compile(textwrap.dedent(input), '<test>', 'exec', PyCF_ONLY_AST)
        except BaseException as e:
            return e
        try:
            exec(textwrap.dedent(input), {})
        except BaseException as e:
            return e

    def flakes(self, input, *expectedOutputs, **kw):
        tree = ast.parse(textwrap.dedent(input))
        file_tokens = checker.make_tokens(textwrap.dedent(input))
        if kw.get('is_segment'):
            tree = tree.body[0]
            kw.pop('is_segment')
        w = checker.Checker(
            tree, file_tokens=file_tokens, withDoctest=self.withDoctest, **kw
        )
        outputs = [type(o) for o in w.messages]
        expectedOutputs = list(expectedOutputs)
        outputs.sort(key=lambda t: t.__name__)
        expectedOutputs.sort(key=lambda t: t.__name__)
        self.assertEqual(outputs, expectedOutputs, '''\
for input:
%s
expected outputs:
%r
but got:
%s''' % (input, expectedOutputs, '\n'.join([str(o) for o in w.messages])))
        return w
