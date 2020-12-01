import ast
import textwrap
import unittest

from pyflakes import checker

__all__ = ['TestCase', 'skip', 'skipIf']

skip = unittest.skip
skipIf = unittest.skipIf


class TestCase(unittest.TestCase):

    withDoctest = False

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
{}
expected outputs:
{!r}
but got:
{}'''.format(input, expectedOutputs, '\n'.join([str(o) for o in w.messages])))
        return w

    if not hasattr(unittest.TestCase, 'assertIs'):

        def assertIs(self, expr1, expr2, msg=None):
            if expr1 is not expr2:
                self.fail(msg or f'{expr1!r} is not {expr2!r}')

    if not hasattr(unittest.TestCase, 'assertIsInstance'):

        def assertIsInstance(self, obj, cls, msg=None):
            """Same as self.assertTrue(isinstance(obj, cls))."""
            if not isinstance(obj, cls):
                self.fail(msg or f'{obj!r} is not an instance of {cls!r}')

    if not hasattr(unittest.TestCase, 'assertNotIsInstance'):

        def assertNotIsInstance(self, obj, cls, msg=None):
            """Same as self.assertFalse(isinstance(obj, cls))."""
            if isinstance(obj, cls):
                self.fail(msg or f'{obj!r} is an instance of {cls!r}')

    if not hasattr(unittest.TestCase, 'assertIn'):

        def assertIn(self, member, container, msg=None):
            """Just like self.assertTrue(a in b)."""
            if member not in container:
                self.fail(msg or f'{member!r} not found in {container!r}')

    if not hasattr(unittest.TestCase, 'assertNotIn'):

        def assertNotIn(self, member, container, msg=None):
            """Just like self.assertTrue(a not in b)."""
            if member in container:
                self.fail(msg or
                          f'{member!r} unexpectedly found in {container!r}')
