from pyflakes import messages as m, test

class Test(test.Test):
    def test_undefined(self):
        self.run('bar', m.UndefinedName)

    def test_definedInListComp(self):
        self.run('[a for a in range(10) if a]')

    def test_definedInGenExp(self):
        self.run('(a for a in xrange(10) if a)')

    def test_functionsNeedGlobalScope(self):
        self.run('''
        class a:
            def b():
                fu
        fu = 1
        ''')

    def test_builtins(self):
        self.run('range(10)')

    def test_magic_globals(self):
        self.run('__file__')

    def test_globalImportStar(self):
        '''Can't find undefined names with import *'''
        self.run('from fu import *; bar', m.ImportStarUsed)

    def test_localImportStar(self):
        '''A local import * still allows undefined names to be found in upper scopes'''
        self.run('''
        def a():
            from fu import *
        bar''', m.ImportStarUsed, m.UndefinedName)

    def test_unpackedParameter(self):
        '''Unpacked function parameters create bindings'''
        self.run('''
        def a((bar, baz)):
            bar; baz
        ''')

    def test_definedByGlobal(self):
        '''"global" can make an otherwise undefined name in another function defined'''
        self.run('''
        def a(): global fu; fu = 1
        def b(): fu
        ''')
    test_definedByGlobal.todo = ''

    def test_del(self):
        '''del deletes bindings'''
        self.run('a = 1; del a; a', m.UndefinedName)

    def test_delGlobal(self):
        '''del a global binding from a function'''
        self.run('''
        a = 1
        def f():
            global a
            del a
        a
        ''')
    test_delGlobal.todo = ''

    def test_delUndefined(self):
        '''del an undefined name'''
        self.run('del a', m.UndefinedName)

    def test_globalFromNestedScope(self):
        '''global names are available from nested scopes'''
        self.run('''
        a = 1
        def b():
            def c():
                a
        ''')

    def test_nestedClass(self):
        '''nested classes can access enclosing scope'''
        self.run('''
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
        self.run('''
        def f():
            class C:
                bar = foo
            foo = 456

        f()
        ''', m.UndefinedName)
