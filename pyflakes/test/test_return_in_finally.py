
from pyflakes import messages as m
from pyflakes.test.harness import TestCase


class Test(TestCase):
    def test_return(self):
        self.flakes('''
        def a(): pass
        def b():
            try:
                a()
            finally:
                return
        ''', m.ReturnInsideFinallyBlock)

    def test_returnWithValue(self):
        self.flakes('''
        def a():
            try:
                x = 1
            finally:
                return x
        ''', m.ReturnInsideFinallyBlock)

    def test_returnInNestedTry1(self):
        self.flakes('''
        def a():
            try:
                pass
            finally:
                try:
                    return
                except:
                    pass
        ''', m.ReturnInsideFinallyBlock)

    def test_returnInNestedTry2(self):
        self.flakes('''
        def a():
            try:
                pass
            finally:
                try:
                    pass
                except:
                    return
        ''', m.ReturnInsideFinallyBlock)

    def test_returnInNestedTry3(self):
        self.flakes('''
        def a():
            try:
                pass
            finally:
                try:
                    pass
                finally:
                    return
        ''', m.ReturnInsideFinallyBlock)

    def test_returnInIf(self):
        self.flakes('''
        def a(): pass
        def b():
            try:
                a()
            finally:
                if a():
                    return
                pass
        ''', m.ReturnInsideFinallyBlock)

    def test_returnInDeepIf(self):
        self.flakes('''
        def a(): pass
        def b():
            try:
                raise ValueError()
            except ValueError:
                pass
            finally:
                if a():
                    while a():
                        for _ in a():
                            return
                pass
        ''', m.ReturnInsideFinallyBlock)

    def test_returnInNestedFunction(self):
        self.flakes('''
        def a():
            try:
                raise ValueError()
            finally:
                def b():
                    return
                pass
        ''')

    def test_returnInNestedClass(self):
        self.flakes('''
        def a():
            try:
                raise ValueError()
            finally:
                class B:
                    def b(self):
                        return
        ''')
