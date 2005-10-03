from pyflakes import messages as m, test

class Test(test.Test):

    def test_unusedImport(self):
        self.run('import fu, bar', m.UnusedImport, m.UnusedImport)
        self.run('from baz import fu, bar', m.UnusedImport, m.UnusedImport)

    def test_aliasedImport(self):
        self.run('import fu as FU, bar as FU', m.RedefinedWhileUnused, m.UnusedImport)
        self.run('from moo import fu as FU, bar as FU', m.RedefinedWhileUnused, m.UnusedImport)

    def test_usedImport(self):
        self.run('import fu; print fu')
        self.run('from baz import fu; print fu')

    def test_redefinedWhileUnused(self):
        self.run('import fu; fu = 3', m.RedefinedWhileUnused)
        self.run('import fu; del fu', m.RedefinedWhileUnused)
        self.run('import fu; fu, bar = 3', m.RedefinedWhileUnused)
        self.run('import fu; [fu, bar] = 3', m.RedefinedWhileUnused)

    def test_redefinedByFunction(self):
        self.run('''
        import fu
        def fu():
            pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedByClass(self):
        self.run('''
        import fu
        class fu:
            pass
        ''', m.RedefinedWhileUnused)

    def test_usedInFunction(self):
        self.run('''
        import fu
        def fun():
            print fu
        ''')

    def test_shadowedByParameter(self):
        self.run('''
        import fu
        def fun(fu):
            print fu
        ''', m.UnusedImport)

        self.run('''
        import fu
        def fun(fu):
            print fu
        print fu
        ''')

    def test_newAssignment(self):
        self.run('fu = None')

    def test_usedInGetattr(self):
        self.run('import fu; fu.bar.baz')
        self.run('import fu; "bar".fu.baz', m.UnusedImport)

    def test_usedInSlice(self):
        self.run('import fu; print fu.bar[1:]')

    def test_usedInIfBody(self):
        self.run('''
        import fu
        if True: print fu
        ''')

    def test_usedInIfConditional(self):
        self.run('''
        import fu
        if fu: pass
        ''')

    def test_usedInElifConditional(self):
        self.run('''
        import fu
        if False: pass
        elif fu: pass
        ''')

    def test_usedInElse(self):
        self.run('''
        import fu
        if False: pass
        else: print fu
        ''')

    def test_usedInCall(self):
        self.run('import fu; fu.bar()')

    def test_usedInClass(self):
        self.run('''
        import fu
        class bar:
            bar = fu
        ''')

    def test_usedInClassBase(self):
        self.run('''
        import fu
        class bar(object, fu.baz):
            pass
        ''')

    def test_notUsedInNestedScope(self):
        self.run('''
        import fu
        def bleh():
            pass
        print fu
        ''')

    def test_usedInFor(self):
        self.run('''
        import fu
        for bar in range(9):
            print fu
        ''')

    def test_usedInForElse(self):
        self.run('''
        import fu
        for bar in range(10):
            pass
        else:
            print fu
        ''')

    def test_redefinedByFor(self):
        self.run('''
        import fu
        for fu in range(2):
            pass
        ''', m.RedefinedWhileUnused)

    def test_usedInReturn(self):
        self.run('''
        import fu
        def fun():
            return fu
        ''')

    def test_usedInOperators(self):
        self.run('import fu; 3 + fu.bar')
        self.run('import fu; 3 % fu.bar')
        self.run('import fu; 3 - fu.bar')
        self.run('import fu; 3 * fu.bar')
        self.run('import fu; 3 ** fu.bar')
        self.run('import fu; 3 / fu.bar')
        self.run('import fu; 3 // fu.bar')
        self.run('import fu; -fu.bar')
        self.run('import fu; ~fu.bar')
        self.run('import fu; 1 == fu.bar')
        self.run('import fu; 1 | fu.bar')
        self.run('import fu; 1 & fu.bar')
        self.run('import fu; 1 ^ fu.bar')
        self.run('import fu; 1 >> fu.bar')
        self.run('import fu; 1 << fu.bar')

    def test_usedInAssert(self):
        self.run('import fu; assert fu.bar')

    def test_usedInSubscript(self):
        self.run('import fu; fu.bar[1]')

    def test_usedInLogic(self):
        self.run('import fu; fu and False')
        self.run('import fu; fu or False')
        self.run('import fu; not fu.bar')

    def test_usedInList(self):
        self.run('import fu; [fu]')

    def test_usedInTuple(self):
        self.run('import fu; (fu,)')

    def test_usedInTry(self):
        self.run('''
        import fu
        try: fu
        except: pass
        ''')

    def test_usedInExcept(self):
        self.run('''
        import fu
        try: fu
        except: pass
        ''')

    def test_redefinedByExcept(self):
        self.run('''
        import fu
        try: pass
        except Exception, fu: pass
        ''', m.RedefinedWhileUnused)

    def test_usedInRaise(self):
        self.run('''
        import fu
        raise fu.bar
        ''')

    def test_usedInYield(self):
        self.run('''
        import fu
        def gen():
            yield fu
        ''')

    def test_usedInDict(self):
        self.run('import fu; {fu:None}')
        self.run('import fu; {1:fu}')

    def test_usedInParameterDefault(self):
        self.run('''
        import fu
        def f(bar=fu):
            pass
        ''')

    def test_usedInAttributeAssign(self):
        self.run('import fu; fu.bar = 1')

    def test_usedInKeywordArg(self):
        self.run('import fu; fu.bar(stuff=fu)')

    def test_usedInAssignment(self):
        self.run('import fu; bar=fu')
        self.run('import fu; n=0; n+=fu')

    def test_usedInListComp(self):
        self.run('import fu; [fu for _ in range(1)]')
        self.run('import fu; [1 for _ in range(1) if fu]')

    def test_redefinedByListComp(self):
        self.run('import fu; [1 for fu in range(1)]', m.RedefinedWhileUnused)

    def test_usedInGenExp(self):
        self.run('import fu; (fu for _ in range(1))')
        self.run('import fu; (1 for _ in range(1) if fu)')

    def test_redefinedByGenExp(self):
        self.run('import fu; (1 for fu in range(1))', m.RedefinedWhileUnused)

    def test_usedAsDecorator(self):
        self.run('''
        from interior import decorate
        @decorate
        def f():
            return "hello"
        ''')
        
        self.run('''
        @decorate
        def f():
            return "hello"
        ''', m.UndefinedName)
        
    def test_usedInTryFinally(self):
        self.run('''
        import fu
        try: pass
        finally: fu
        ''')

        self.run('''
        import fu
        try: fu
        finally: pass
        ''')

    def test_usedInWhile(self):
        self.run('''
        import fu
        while 0:
            fu
        ''')

        self.run('''
        import fu
        while fu: pass
        ''')

    def test_usedInGlobal(self):
        self.run('''
        import fu
        def f(): global fu
        ''', m.UnusedImport)

    def test_usedInBackquote(self):
        self.run('import fu; `fu`')

    def test_usedInExec(self):
        self.run('import fu; exec "print 1" in fu.bar')

    def test_usedInLambda(self):
        self.run('import fu; lambda: fu')

    def test_shadowedByLambda(self):
        self.run('import fu; lambda fu: fu', m.UnusedImport)

    def test_usedInSliceObj(self):
        self.run('import fu; "meow"[::fu]')

    def test_unusedInNestedScope(self):
        self.run('''
        def bar():
            import fu
        fu
        ''', m.UnusedImport, m.UndefinedName)

    def test_methodsDontUseClassScope(self):
        self.run('''
        class bar:
            import fu
            def fun(self):
                fu
        ''', m.UnusedImport, m.UndefinedName)

    def test_nestedFunctionsNestScope(self):
        self.run('''
        def a():
            def b():
                fu
            import fu
        ''')

    def test_nestedClassAndFunctionScope(self):
        self.run('''
        def a():
            import fu
            class b:
                def c(self):
                    print fu
        ''')

    def test_importStar(self):
        self.run('from fu import *', m.ImportStarUsed)

    def test_packageImport(self):
        self.run('import fu.bar; fu.bar')
    test_packageImport.todo = "this has been hacked to treat 'import fu.bar' as just 'import fu'"

    def test_assignRHSFirst(self):
        self.run('import fu; fu = fu')
        self.run('import fu; fu, bar = fu')
        self.run('import fu; [fu, bar] = fu')
        self.run('import fu; fu += fu')

    def test_tryingMultipleImports(self):
        self.run('''
        try:
            import fu
        except ImportError:
            import bar as fu
        ''')
    test_tryingMultipleImports.todo = ''

    def test_nonGlobalDoesNotRedefine(self):
        self.run('''
        import fu
        def a():
            fu = 3
        fu
        ''')

    def test_functionsRunLater(self):
        self.run('''
        def a():
            fu
        import fu
        ''')

    def test_functionNamesAreBoundNow(self):
        self.run('''
        import fu
        def fu():
            fu
        fu
        ''', m.RedefinedWhileUnused)

    def test_ignoreNonImportRedefinitions(self):
        self.run('a = 1; a = 2')

    def test_importingForImportError(self):
        self.run('''
        try:
            import fu
        except ImportError:
            pass
        ''')
    test_importingForImportError.todo = ''

    def test_explicitlyPublic(self):
        '''imports mentioned in __all__ are not unused'''
        self.run('import fu; __all__ = ["fu"]')
    test_explicitlyPublic.todo = "this would require importing the module or doing smarter parsing"

    def test_importedInClass(self):
        '''Imports in class scope can be used through self'''
        self.run('''
        class c:
            import i
            def __init__(self):
                self.i
        ''')
    test_importedInClass.todo = 'requires evaluating attribute access'

    def test_futureImport(self):
        '''__future__ is special'''
        self.run('from __future__ import division')
