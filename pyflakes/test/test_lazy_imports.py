from sys import version_info

from pyflakes import messages as m
from pyflakes.test.harness import TestCase, skipIf


@skipIf(version_info < (3, 15), 'new in Python 3.15')
class Test(TestCase):
    def test_unused_lazy_imports(self):
        self.flakes('''
        lazy import x
        lazy from y import z
        ''', m.UnusedImport, m.UnusedImport)

    def test_lazy_star_import_not_allowed(self):
        self.flakes('''
        lazy from x import *
        ''', m.LazyImportStarNotPermitted)

    def test_lazy_import_not_at_module_scope(self):
        self.flakes('''
        def f():
            lazy import x
        class C:
            lazy from y import z
        ''', m.LazyImportNotAtModuleScope, m.LazyImportNotAtModuleScope)

    def test_lazy_imports_eager_use_ok(self):
        self.flakes('''
        lazy from x import y

        x: y = ...                 # ok in annotations
        type q = y                 # ok in type aliases
        def f1(u: y) -> y: ...     # ok in function annotations
        def f2(): print(y)         # ok in nested scope
        x = (y for _ in [])        # ok not in generator iter
        ''')

    def test_lazy_imports_eager_use_error(self):
        self.flakes('''
        lazy from x import y
        z = y                     # module scope

        class C:
            z = y                 # class scope

        match y:                  # match expression
            case y.attr: pass     # case attribute

        (_ for _ in y)            # generator expression iterable

        [y for _ in [...]]        # evaluated comprehensions
        {y for _ in [...]}        # evaluated comprehensions
        {0: y for _ in [...]}     # evaluated comprehensions

        ''', *([m.EagerUseOfLazyImport] * 8))

    def test_lazy_imports_eager_use_in_type_alias(self):
        self.flakes('''
        from typing import TypeAlias
        lazy from x import y
        alias: TypeAlias = y      # evaluated eagerly
        ''', m.EagerUseOfLazyImport)
