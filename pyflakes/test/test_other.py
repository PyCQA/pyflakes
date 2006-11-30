from pyflakes import messages as m
from pyflakes.test import harness

class Test(harness.Test):

    def test_duplicateArgs(self):
        self.flakes('def fu(bar, bar): pass', m.DuplicateArgument)

    def test_localReferencedBeforeAssignment(self):
        self.flakes('''
        a = 1
        def f():
            a; a=1
        f()
        ''', m.UndefinedName)
    test_localReferencedBeforeAssignment.todo = 'this requires finding all assignments in the function body first'

    def test_redefinedFunction(self):
        """
        Test that shadowing a function definition with another one raises a
        warning.
        """
        self.flakes('''
        def a(): pass
        def a(): pass
        ''', m.RedefinedFunction)

    def test_redefinedClassFunction(self):
        """
        Test that shadowing a function definition in a class suite with another
        one raises a warning.
        """
        self.flakes('''
        class A:
            def a(): pass
            def a(): pass
        ''', m.RedefinedFunction)

    def test_functionDecorator(self):
        """
        Test that shadowing a function definition with a decorated version of
        that function does not raise a warning.
        """
        self.flakes('''
        from somewhere import somedecorator

        def a(): pass
        a = somedecorator(a)
        ''')

    def test_classFunctionDecorator(self):
        """
        Test that shadowing a function definition in a class suite with a
        decorated version of that function does not raise a warning.
        """
        self.flakes('''
        class A:
            def a(): pass
            a = classmethod(a)
        ''')

    def test_unaryPlus(self):
        '''Don't die on unary +'''
        self.flakes('+1')
