from pyflakes import messages as m
from pyflakes.test import harness

class Test(harness.Test):
    def test_undefined(self):
        self.flakes('bar', m.UndefinedName)

    def test_definedInListComp(self):
        self.flakes('[a for a in range(10) if a]')

    def test_definedInGenExp(self):
        self.flakes('(a for a in xrange(10) if a)')

    def test_functionsNeedGlobalScope(self):
        self.flakes('''
        class a:
            def b():
                fu
        fu = 1
        ''')

    def test_builtins(self):
        self.flakes('range(10)')

    def test_magic_globals(self):
        self.flakes('__file__')

    def test_globalImportStar(self):
        '''Can't find undefined names with import *'''
        self.flakes('from fu import *; bar', m.ImportStarUsed)

    def test_localImportStar(self):
        '''A local import * still allows undefined names to be found in upper scopes'''
        self.flakes('''
        def a():
            from fu import *
        bar
        ''', m.ImportStarUsed, m.UndefinedName)

    def test_unpackedParameter(self):
        '''Unpacked function parameters create bindings'''
        self.flakes('''
        def a((bar, baz)):
            bar; baz
        ''')

    def test_definedByGlobal(self):
        '''"global" can make an otherwise undefined name in another function defined'''
        self.flakes('''
        def a(): global fu; fu = 1
        def b(): fu
        ''')
    test_definedByGlobal.todo = ''

    def test_del(self):
        '''del deletes bindings'''
        self.flakes('a = 1; del a; a', m.UndefinedName)

    def test_delGlobal(self):
        '''del a global binding from a function'''
        self.flakes('''
        a = 1
        def f():
            global a
            del a
        a
        ''')

    def test_delUndefined(self):
        '''del an undefined name'''
        self.flakes('del a', m.UndefinedName)

    def test_globalFromNestedScope(self):
        '''global names are available from nested scopes'''
        self.flakes('''
        a = 1
        def b():
            def c():
                a
        ''')

    def test_laterRedefinedGlobalFromNestedScope(self):
        """
        Test that referencing a local name that shadows a global, before it is
        defined, generates a warning.
        """
        self.flakes('''
        a = 1
        def fun():
            a
            a = 2
        ''', m.UndefinedLocal)

    def test_laterRedefinedGlobalFromNestedScope2(self):
        """
        Test that referencing a local name in a nested scope that shadows a
        global declared in an enclosing scope, before it is defined, generates
        a warning.
        """
        self.flakes('''
            a = 1
            def fun():
                global a
                def fun2():
                    a
                    a = 2
        ''', m.UndefinedLocal)

    def test_laterRedefinedGlobalFromNestedScope3(self):
        """
        Test that referencing a local name in a nested scope that shadows a
        global, before it is defined, generates a warning.
        """
        self.flakes('''
            def fun():
                a = 1
                def fun2():
                    a
                    a = 1
        ''', m.UndefinedLocal)

    def test_nestedClass(self):
        '''nested classes can access enclosing scope'''
        self.flakes('''
        def f(foo):
            class C:
                bar = foo
                def f(self):
                    return foo
            return C()

        f(123).f()
        ''')

    def test_badNestedClass(self):
        '''free variables in nested classes must bind at class creation'''
        self.flakes('''
        def f():
            class C:
                bar = foo
            foo = 456

        f()
        ''', m.UndefinedName)
