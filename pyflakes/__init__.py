# (c) 2005 Divmod, Inc.  See LICENSE file for details

import __builtin__
from pyflakes import messages

class Binding(object):
    def __init__(self, name, source):
        self.name = name
        self.source = source
        self.used = False

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Importation object %r from line %r at 0x%x>' % (self.name, self.source.lineno, id(self))

class UnBinding(Binding):
    '''Created by the 'del' operator.'''

class Importation(Binding):
    def __init__(self, name, source):
        name = name.split('.')[0]
        super(Importation, self).__init__(name, source)

class Assignment(Binding):
    pass


class Scope(dict):
    importStarred = False       # set to True when import * is found

    def __repr__(self):
        return '<%s at 0x%x %s>' % (self.__class__.__name__, id(self), dict.__repr__(self))

    def __init__(self):
        super(Scope, self).__init__()

class ClassScope(Scope):
    pass

class FunctionScope(Scope):
    pass

class ModuleScope(Scope):
    pass


class Checker(object):
    nodeDepth = 0
    traceTree = False

    def __init__(self, tree, filename='(none)'):
        self.deferred = []
        self.dead_scopes = []
        self.messages = []
        self.filename = filename
        self.scopeStack = [ModuleScope()]

        self.handleChildren(tree)
        for handler, scope in self.deferred:
            self.scopeStack = scope
            handler()
        del self.scopeStack[1:]
        self.popScope()
        self.check_dead_scopes()

    def defer(self, callable):
        '''Schedule something to be called after just before completion.

        This is used for handling function bodies, which must be deferred
        because code later in the file might modify the global scope. When
        `callable` is called, the scope at the time this is called will be
        restored, however it will contain any new bindings added to it.
        '''
        self.deferred.append( (callable, self.scopeStack[:]) )

    def scope(self):
        return self.scopeStack[-1]
    scope = property(scope)

    def popScope(self):
        self.dead_scopes.append(self.scopeStack.pop())

    def check_dead_scopes(self):
        for scope in self.dead_scopes:
            for importation in scope.itervalues():
                if isinstance(importation, Importation) and not importation.used:
                    self.report(messages.UnusedImport, importation.source.lineno, importation.name)

    def pushFunctionScope(self):
        self.scopeStack.append(FunctionScope())

    def pushClassScope(self):
        self.scopeStack.append(ClassScope())

    def report(self, messageClass, *args, **kwargs):
        self.messages.append(messageClass(self.filename, *args, **kwargs))

    def handleChildren(self, tree):
        for node in tree.getChildNodes():
            self.handleNode(node)

    def handleNode(self, node):
        if self.traceTree:
            print '  ' * self.nodeDepth + node.__class__.__name__
        self.nodeDepth += 1
        try:
            handler = getattr(self, node.__class__.__name__.upper())
            handler(node)
        finally:
            self.nodeDepth -= 1
        if self.traceTree:
            print '  ' * self.nodeDepth + 'end ' + node.__class__.__name__

    def ignore(self, node):
        pass

    STMT = PRINT = PRINTNL = TUPLE = LIST = ASSTUPLE = ASSATTR = \
    ASSLIST = GETATTR = SLICE = SLICEOBJ = IF = CALLFUNC = DISCARD = FOR = \
    RETURN = ADD = MOD = SUB = NOT = UNARYSUB = INVERT = ASSERT = COMPARE = \
    SUBSCRIPT = AND = OR = TRYEXCEPT = RAISE = YIELD = DICT = LEFTSHIFT = \
    RIGHTSHIFT = KEYWORD = TRYFINALLY = WHILE = EXEC = MUL = DIV = POWER = \
    FLOORDIV = BITAND = BITOR = BITXOR = LISTCOMPFOR = LISTCOMPIF = \
    AUGASSIGN = BACKQUOTE = UNARYADD = GENEXPR = GENEXPRFOR = GENEXPRIF = handleChildren

    CONST = PASS = CONTINUE = BREAK = GLOBAL = ELLIPSIS = ignore

    def addBinding(self, lineno, value, reportRedef=True):
        '''Called when a binding is altered.

        - `lineno` is the line of the statement responsible for the change
        - `value` is the optional new value, a Binding instance, associated
          with the binding; if None, the binding is deleted if it exists.
        - iff `reportRedef` is True (default), rebinding while unused will be
          reported.
        '''
        if isinstance(self.scope.get(value.name), Importation) \
        and not self.scope[value.name].used \
        and reportRedef:
            self.report(messages.RedefinedWhileUnused, lineno, value.name, self.scope[value.name].source.lineno)

        if isinstance(value, UnBinding):
            try:
                del self.scope[value.name]
            except KeyError:
                self.report(messages.UndefinedName, lineno, value.name)
        else:
            self.scope[value.name] = value


    def LISTCOMP(self, node):
        for qual in node.quals:
            self.handleNode(qual)
        self.handleNode(node.expr)

    GENEXPRINNER = LISTCOMP

    def NAME(self, node):
        # try local scope
        importStarred = self.scope.importStarred
        try:
            self.scope[node.name].used = True
        except KeyError:
            pass
        else:
            return

        # try enclosing function scopes

        for scope in self.scopeStack[-2:0:-1]:
            importStarred = importStarred or scope.importStarred
            if not isinstance(scope, FunctionScope):
                continue
            try:
                scope[node.name].used = True
            except KeyError:
                pass
            else:
                return

        # try global scope

        importStarred = importStarred or self.scopeStack[0].importStarred
        try:
            self.scopeStack[0][node.name].used = True
        except KeyError:
            if (not hasattr(__builtin__, node.name)) \
            and node.name not in ['__file__'] \
            and not importStarred:
                self.report(messages.UndefinedName, node.lineno, node.name)


    def FUNCTION(self, node):
        if getattr(node, "decorators", None) is not None:
            self.handleChildren(node.decorators)
        self.addBinding(node.lineno, Assignment(node.name, node))
        self.LAMBDA(node)

    def LAMBDA(self, node):
        for default in node.defaults:
            self.handleNode(default)

        def runFunction():
            args = []

            def addArgs(arglist):
                for arg in arglist:
                    if isinstance(arg, tuple):
                        addArgs(arg)
                    else:
                        if arg in args:
                            self.report(messages.DuplicateArgument, node.lineno, arg)
                        args.append(arg)

            self.pushFunctionScope()
            addArgs(node.argnames)
            for name in args:
                self.addBinding(node.lineno, Assignment(name, node), reportRedef=False)
            self.handleNode(node.code)
            self.popScope()

        self.defer(runFunction)

    def CLASS(self, node):
        self.addBinding(node.lineno, Assignment(node.name, node))
        for baseNode in node.bases:
            self.handleNode(baseNode)
        self.pushClassScope()
        self.handleChildren(node.code)
        self.popScope()

    def ASSNAME(self, node):
        if node.flags == 'OP_DELETE':
            self.addBinding(node.lineno, UnBinding(node.name, node))
        else:
            self.addBinding(node.lineno, Assignment(node.name, node))

    def ASSIGN(self, node):
        self.handleNode(node.expr)
        for subnode in node.nodes[::-1]:
            self.handleNode(subnode)

    def IMPORT(self, node):
        for name, alias in node.names:
            name = alias or name
            importation = Importation(name, node)
            self.addBinding(node.lineno, importation)

    def FROM(self, node):
        for name, alias in node.names:
            if name == '*':
                self.scope.importStarred = True
                self.report(messages.ImportStarUsed, node.lineno, node.modname)
                continue
            name = alias or name
            importation = Importation(name, node)
            if node.modname == '__future__':
                importation.used = True
            self.addBinding(node.lineno, importation)
