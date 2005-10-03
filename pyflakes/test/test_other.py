from pyflakes import messages as m, test

class Test(test.Test):

    def test_duplicateArgs(self):
        self.run('def fu(bar, bar): pass', m.DuplicateArgument)

    def test_localReferencedBeforeAssignment(self):
        self.run('''
        a = 1
        def f():
            a; a=1
        f()
        ''', m.UndefinedName)
    test_localReferencedBeforeAssignment.todo = 'this requires finding all assignments in the function body first'

    def test_redefinedFunction(self):
        self.run('''
        def a(): pass
        def a(): pass
        ''', m.RedefinedFunction)
    test_redefinedFunction.todo = 'easy to implement'

    def test_unaryPlus(self):
        '''Don't die on unary +'''
        self.run('+1')
