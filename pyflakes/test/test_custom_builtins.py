import contextlib
import os
from unittest import mock
from pyflakes import messages as m
from pyflakes.test.harness import TestCase
from pyflakes.checker import _custom_builtins


@contextlib.contextmanager
def _clear_custom_builtins_cache():
    _custom_builtins.cache_clear()
    try:
        yield
    finally:
        _custom_builtins.cache_clear()


class TestCustomBuiltins(TestCase):
    def test_custom_builtins_from_init(self):
        self.flakes('unknown', m.UndefinedName)
        self.flakes('unknown', builtins=('unknown',))

    def test_custom_builtins_from_env(self):
        self.flakes('y = a + b', m.UndefinedName, m.UndefinedName)
        with (
                _clear_custom_builtins_cache(),
                mock.patch.dict(os.environ, {'PYFLAKES_BUILTINS': 'a,b'}),
        ):
            self.flakes('y = a + b')
