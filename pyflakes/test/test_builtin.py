"""
Tests for detecting redefinition of builtins.
"""
from sys import version_info

from pyflakes import messages as m
from pyflakes.checker import Checker
from pyflakes.test.harness import TestCase, skipIf

try:
    WindowsError
    WIN = True
except NameError:
    WIN = False


class TestBuiltins(TestCase):

    def test_builtin_unbound_local(self):
        self.flakes('''
        def foo():
            a = range(1, 10)
            range = a
            return range

        foo()

        print(range)
        ''', m.UndefinedLocal)

    def test_global_shadowing_builtin(self):
        self.flakes('''
        def f():
            global range
            range = None
            print(range)

        f()
        ''')

    @skipIf(version_info >= (3,), 'not an UnboundLocalError in Python 3')
    def test_builtin_in_comprehension(self):
        self.flakes('''
        def f():
            [range for range in range(1, 10)]

        f()
        ''', m.UndefinedLocal)


class TestLiveBuiltins(TestCase):

    def test_exists(self):
        for name in sorted(Checker.builtIns):
            # __file__ does exist in this test harness
            if name == '__file__':
                continue

            if name == 'WindowsError' and not WIN:
                continue

            source = '''
            %s
            ''' % name
            e = self.pythonException(source)
            self.assertIsNone(e)

    def test_del(self):
        for name in sorted(Checker.builtIns):
            # __file__ does exist in this test harness
            if name == '__file__':
                continue

            # __debug__ can be deleted sometimes and not deleted other times.
            # Safest course of action is to assume it can be deleted, in
            # order that no error is reported by pyflakes
            if name == '__debug__':
                continue

            source = '''
            del %s
            ''' % name

            e = self.pythonException(source)

            if isinstance(e, SyntaxError):
                if version_info < (3,):
                    # SyntaxError: invalid syntax
                    self.assertIn(name, ('print'))
                else:
                    # SyntaxError: can't delete keyword
                    self.assertIn(name, ('None', 'True', 'False'))
            elif isinstance(e, NameError):
                self.flakes(source, m.UndefinedName)
            else:
                self.flakes(source)
