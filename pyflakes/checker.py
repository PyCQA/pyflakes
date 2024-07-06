#@+leo-ver=5-thin
#@+node:ekr.20240702085302.1: * @file C:\Repos\ekr-fork-pyflakes\pyflakes\checker.py
"""
Main module.

Implement the central Checker class.
Also, it models the Bindings and Scopes.
"""
#@+<< checker.py: imports and annotations >>
#@+node:ekr.20240703054405.1: ** << checker.py: imports and annotations >>
import __future__
import builtins
import ast
import collections
import contextlib
import doctest
import functools
import os
import re
import string
import sys
### import warnings

from pyflakes import messages

Node = ast.AST
#@-<< checker.py: imports and annotations >>

if 1:
    leo_path = r'C:\Repos\leo-editor'
    if leo_path not in sys.path:
        sys.path.insert(1, leo_path)
    from leo.core import leoGlobals as g
    assert g

# < < checker.py: NEW switch > >
#@+<< checker.py: globals >>
#@+node:ekr.20240702085302.2: ** << checker.py: globals >>
PYPY = hasattr(sys, 'pypy_version_info')
builtin_vars = dir(builtins)
parse_format_string = string.Formatter().parse
FOR_TYPES = (ast.For, ast.AsyncFor)

MAPPING_KEY_RE = re.compile(r'\(([^()]*)\)')
CONVERSION_FLAG_RE = re.compile('[#0+ -]*')
WIDTH_RE = re.compile(r'(?:\*|\d*)')
PRECISION_RE = re.compile(r'(?:\.(?:\*|\d*))?')
LENGTH_RE = re.compile('[hlL]?')
# https://docs.python.org/3/library/stdtypes.html#old-string-formatting
VALID_CONVERSIONS = frozenset('diouxXeEfFgGcrsa%')

# Globally defined names which are not attributes of the builtins module, or
# are only present on some platforms.
_MAGIC_GLOBALS = ['__file__', '__builtins__', '__annotations__', 'WindowsError']

TYPING_MODULES = frozenset(('typing', 'typing_extensions'))

#@-<< checker.py: globals >>


#@+others
#@+node:ekr.20240702105119.1: ** checker.py: Utility classes
#@+node:ekr.20240702085302.70: *3* class DetectClassScopedMagic
class DetectClassScopedMagic:
    names = dir()


#@+node:ekr.20240702085302.24: *3* class UnhandledKeyType
class UnhandledKeyType:
    """
    A dictionary key of a type that we cannot or do not check for duplicates.
    """


#@+node:ekr.20240702085302.25: *3* class VariableKey
class VariableKey:
    """
    A dictionary key which is a variable.

    @ivar item: The variable AST object.
    """
    #@+others
    #@+node:ekr.20240702085302.26: *4* VariableKey.__init__
    def __init__(self, item):
        self.name = item.id

    #@+node:ekr.20240702085302.27: *4* VariableKey.__eq__
    def __eq__(self, compare):
        return (
            compare.__class__ == self.__class__ and
            compare.name == self.name
        )

    #@+node:ekr.20240702085302.28: *4* VariableKey.__hash__
    def __hash__(self):
        return hash(self.name)


    #@-others
#@+node:ekr.20240702085302.3: ** checker.py: Utils
#@+node:ekr.20240702085302.4: *3* function: getAlternatives
def getAlternatives(n):
    if isinstance(n, ast.If):
        return [n.body]
    elif isinstance(n, ast.Try):
        return [n.body + n.orelse] + [[hdl] for hdl in n.handlers]
    elif sys.version_info >= (3, 10) and isinstance(n, ast.Match):
        return [mc.body for mc in n.cases]


#@+node:ekr.20240702085302.6: *3* function: _is_singleton
def _is_singleton(node):  # type: (ast.AST) -> bool
    return (
        isinstance(node, ast.Constant) and
        isinstance(node.value, (bool, type(Ellipsis), type(None)))
    )


#@+node:ekr.20240702085302.7: *3* function: _is_tuple_constant
def _is_tuple_constant(node):  # type: (ast.AST) -> bool
    return (
        isinstance(node, ast.Tuple) and
        all(_is_constant(elt) for elt in node.elts)
    )


#@+node:ekr.20240702085302.8: *3* function: _is_constant
def _is_constant(node):
    return isinstance(node, ast.Constant) or _is_tuple_constant(node)


#@+node:ekr.20240702085302.9: *3* function: _is_const_non_singleton
def _is_const_non_singleton(node):  # type: (ast.AST) -> bool
    return _is_constant(node) and not _is_singleton(node)


#@+node:ekr.20240702085302.10: *3* function: _is_name_or_attr
def _is_name_or_attr(node, name):  # type: (ast.AST, str) -> bool
    return (
        (isinstance(node, ast.Name) and node.id == name) or
        (isinstance(node, ast.Attribute) and node.attr == name)
    )


#@+node:ekr.20240702085302.12: *3* function: _must_match
def _must_match(regex, string, pos):
    match = regex.match(string, pos)
    assert match is not None
    return match


#@+node:ekr.20240702085302.13: *3* function: parse_percent_format
def parse_percent_format(s):
    """Parses the string component of a `'...' % ...` format call

    Copied from https://github.com/asottile/pyupgrade at v1.20.1
    """

    def _parse_inner():
        string_start = 0
        string_end = 0
        in_fmt = False

        i = 0
        while i < len(s):
            if not in_fmt:
                try:
                    i = s.index('%', i)
                except ValueError:  # no more % fields!
                    yield s[string_start:], None
                    return
                else:
                    string_end = i
                    i += 1
                    in_fmt = True
            else:
                key_match = MAPPING_KEY_RE.match(s, i)
                if key_match:
                    key = key_match.group(1)
                    i = key_match.end()
                else:
                    key = None

                conversion_flag_match = _must_match(CONVERSION_FLAG_RE, s, i)
                conversion_flag = conversion_flag_match.group() or None
                i = conversion_flag_match.end()

                width_match = _must_match(WIDTH_RE, s, i)
                width = width_match.group() or None
                i = width_match.end()

                precision_match = _must_match(PRECISION_RE, s, i)
                precision = precision_match.group() or None
                i = precision_match.end()

                # length modifier is ignored
                i = _must_match(LENGTH_RE, s, i).end()

                try:
                    conversion = s[i]
                except IndexError:
                    raise ValueError('end-of-string while parsing format')
                i += 1

                fmt = (key, conversion_flag, width, precision, conversion)
                yield s[string_start:string_end], fmt

                in_fmt = False
                string_start = i

        if in_fmt:
            raise ValueError('end-of-string while parsing format')

    return tuple(_parse_inner())


#@+node:ekr.20240702085302.16: *3* function: convert_to_value
def convert_to_value(item):
    if isinstance(item, ast.Constant):
        return item.value
    elif isinstance(item, ast.Tuple):
        return tuple(convert_to_value(i) for i in item.elts)
    elif isinstance(item, ast.Name):
        return VariableKey(item=item)
    else:
        return UnhandledKeyType()


#@+node:ekr.20240702085302.17: *3* function: is_notimplemented_name_node
def is_notimplemented_name_node(node):
    return isinstance(node, ast.Name) and getNodeName(node) == 'NotImplemented'


#@+node:ekr.20240702085302.72: *3* function: getNodeName
def getNodeName(node):
    # Returns node.id, or node.name, or None
    if hasattr(node, 'id'):     # One of the many nodes with an id
        return node.id
    if hasattr(node, 'name'):   # an ExceptHandler node
        return node.name
    if hasattr(node, 'rest'):   # a MatchMapping node
        return node.rest


#@+node:ekr.20240702104745.1: ** checker.py: Binding classes
#@+node:ekr.20240702085302.18: *3* class Binding
class Binding:
    """
    Represents the binding of a value to a name.

    The checker uses this to keep track of which names have been bound and
    which names have not. See L{Assignment} for a special type of binding that
    is checked with stricter rules.

    @ivar used: pair of (L{Scope}, node) indicating the scope and
                the node that this binding was last used.
    """

    def __init__(self, name, source):
        self.name = name
        self.source = source
        self.used = False

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<{} object {!r} from line {!r} at 0x{:x}>'.format(
            self.__class__.__name__,
            self.name,
            self.source.lineno,
            id(self),
        )

    def redefines(self, other):
        return isinstance(other, Definition) and self.name == other.name


#@+node:ekr.20240702085302.51: *3* class Argument(Binding)
class Argument(Binding):
    """
    Represents binding a name as an argument.
    """


#@+node:ekr.20240702085302.52: *3* class Assignment(Binding) & NamedExprAssignment(Assignment)
class Assignment(Binding):
    """
    Represents binding a name with an explicit assignment.

    The checker will raise warnings for any Assignment that isn't used. Also,
    the checker does not consider assignments in tuple/list unpacking to be
    Assignments, rather it treats them as simple Bindings.
    """


class NamedExprAssignment(Assignment):
    """
    Represents binding a name with an assignment expression.
    """


#@+node:ekr.20240702085302.53: *3* class Annotation(Binding)
class Annotation(Binding):
    """
    Represents binding a name to a type without an associated value.

    As long as this name is not assigned a value in another binding, it is considered
    undefined for most purposes. One notable exception is using the name as a type
    annotation.
    """

    #@+others
    #@+node:ekr.20240702085302.54: *4* Annotation.redefines
    def redefines(self, other):
        """An Annotation doesn't define any name, so it cannot redefine one."""
        return False


    #@-others
#@+node:ekr.20240702085302.57: *3* class ExportBinding(Binding)
class ExportBinding(Binding):
    """
    A binding created by an C{__all__} assignment.  If the names in the list
    can be determined statically, they will be treated as names for export and
    additional checking applied to them.

    The only recognized C{__all__} assignment via list/tuple concatenation is in the
    following format:

        __all__ = ['a'] + ['b'] + ['c']

    Names which are imported and not otherwise used but appear in the value of
    C{__all__} will not have an unused import warning reported for them.
    """

    #@+others
    #@+node:ekr.20240702085302.58: *4* ExportBinding.__init__
    def __init__(self, name, source, scope):
        if '__all__' in scope and isinstance(source, ast.AugAssign):
            self.names = list(scope['__all__'].names)
        else:
            self.names = []

        def _add_to_names(container):
            for node in container.elts:
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    self.names.append(node.value)

        if isinstance(source.value, (ast.List, ast.Tuple)):
            _add_to_names(source.value)
        # If concatenating lists or tuples
        elif isinstance(source.value, ast.BinOp):
            currentValue = source.value
            while isinstance(currentValue.right, (ast.List, ast.Tuple)):
                left = currentValue.left
                right = currentValue.right
                _add_to_names(right)
                # If more lists are being added
                if isinstance(left, ast.BinOp):
                    currentValue = left
                # If just two lists are being added
                elif isinstance(left, (ast.List, ast.Tuple)):
                    _add_to_names(left)
                    # All lists accounted for - done
                    break
                # If not list concatenation
                else:
                    break
        super().__init__(name, source)


    #@-others
#@+node:ekr.20240702104659.1: ** checker.py: Definition classes
#@+node:ekr.20240702085302.19: *3*  class Definition(Binding)
class Definition(Binding):
    """
    A binding that defines a function or a class.
    """
    #@+others
    #@+node:ekr.20240702085302.20: *4* Definition.redefines
    def redefines(self, other):
        return (
            super().redefines(other) or
            (isinstance(other, Assignment) and self.name == other.name)
        )


    #@-others
#@+node:ekr.20240702085302.30: *3*  class Importation(Definition)
class Importation(Definition):
    """
    A binding created by an import statement.

    @ivar fullName: The complete name given to the import statement,
        possibly including multiple dotted components.
    @type fullName: C{str}
    """

    #@+others
    #@+node:ekr.20240702085302.31: *4* Importation.__init__
    def __init__(self, name, source, full_name=None):
        self.fullName = full_name or name
        self.redefined = []
        super().__init__(name, source)

    #@+node:ekr.20240702085302.32: *4* Importation.redefines
    def redefines(self, other):
        if isinstance(other, SubmoduleImportation):
            # See note in SubmoduleImportation about RedefinedWhileUnused
            return self.fullName == other.fullName
        return isinstance(other, Definition) and self.name == other.name

    #@+node:ekr.20240702085302.33: *4* Importation._has_alias
    def _has_alias(self):
        """Return whether importation needs an as clause."""
        return not self.fullName.split('.')[-1] == self.name

    #@+node:ekr.20240702085302.34: *4* Importation.source_statement
    @property
    def source_statement(self):
        """Generate a source statement equivalent to the import."""
        if self._has_alias():
            return f'import {self.fullName} as {self.name}'
        else:
            return 'import %s' % self.fullName

    #@+node:ekr.20240702085302.35: *4* Importation.__str__
    def __str__(self):
        """Return import full name with alias."""
        if self._has_alias():
            return self.fullName + ' as ' + self.name
        else:
            return self.fullName


    #@-others
#@+node:ekr.20240702085302.41: *3*  class ImportationFrom(Importation)
class ImportationFrom(Importation):

    #@+others
    #@+node:ekr.20240702085302.42: *4* ImportationFrom.__init__
    def __init__(self, name, source, module, real_name=None):
        self.module = module
        self.real_name = real_name or name

        if module.endswith('.'):
            full_name = module + self.real_name
        else:
            full_name = module + '.' + self.real_name

        super().__init__(name, source, full_name)

    #@+node:ekr.20240702085302.43: *4* ImportationFrom.__str__
    def __str__(self):
        """Return import full name with alias."""
        if self.real_name != self.name:
            return self.fullName + ' as ' + self.name
        else:
            return self.fullName

    #@+node:ekr.20240702085302.44: *4* ImportationFrom.source_statement
    @property
    def source_statement(self):
        if self.real_name != self.name:
            return f'from {self.module} import {self.real_name} as {self.name}'
        else:
            return f'from {self.module} import {self.name}'


    #@-others
#@+node:ekr.20240702085302.21: *3* class Builtin(Definition)
class Builtin(Definition):
    """A definition created for all Python builtins."""

    #@+others
    #@+node:ekr.20240702085302.22: *4* Builtin.__init__
    def __init__(self, name):
        super().__init__(name, None)

    #@+node:ekr.20240702085302.23: *4* Builtin.__repr__
    def __repr__(self):
        return '<{} object {!r} at 0x{:x}>'.format(
            self.__class__.__name__,
            self.name,
            id(self)
        )


    #@-others
#@+node:ekr.20240702085302.56: *3* class ClassDefinition(Definition)
class ClassDefinition(Definition):
    pass


#@+node:ekr.20240702085302.55: *3* class FunctionDefinition(Definition)
class FunctionDefinition(Definition):
    pass


#@+node:ekr.20240702085302.49: *3* class FutureImportation(ImportationFrom)
class FutureImportation(ImportationFrom):
    """
    A binding created by a from `__future__` import statement.

    `__future__` imports are implicitly used.
    """

    #@+others
    #@+node:ekr.20240702085302.50: *4* FutureImportation.__init__
    def __init__(self, name, source, scope):
        super().__init__(name, source, '__future__')
        self.used = (scope, source)


    #@-others
#@+node:ekr.20240702085302.45: *3* class StarImportation(Importation)
class StarImportation(Importation):
    """A binding created by a 'from x import *' statement."""

    #@+others
    #@+node:ekr.20240702085302.46: *4* StarImportation.__init__
    def __init__(self, name, source):
        super().__init__('*', source)
        # Each star importation needs a unique name, and
        # may not be the module name otherwise it will be deemed imported
        self.name = name + '.*'
        self.fullName = name

    #@+node:ekr.20240702085302.47: *4* StarImportation.source_statement
    @property
    def source_statement(self):
        return 'from ' + self.fullName + ' import *'

    #@+node:ekr.20240702085302.48: *4* StarImportation.__str__
    def __str__(self):
        # When the module ends with a ., avoid the ambiguous '..*'
        if self.fullName.endswith('.'):
            return self.source_statement
        else:
            return self.name


    #@-others
#@+node:ekr.20240702085302.36: *3* class SubmoduleImportation(Importation)
class SubmoduleImportation(Importation):
    """
    A binding created by a submodule import statement.

    A submodule import is a special case where the root module is implicitly
    imported, without an 'as' clause, and the submodule is also imported.
    Python does not restrict which attributes of the root module may be used.

    This class is only used when the submodule import is without an 'as' clause.

    pyflakes handles this case by registering the root module name in the scope,
    allowing any attribute of the root module to be accessed.

    RedefinedWhileUnused is suppressed in `redefines` unless the submodule
    name is also the same, to avoid false positives.
    """

    #@+others
    #@+node:ekr.20240702085302.37: *4* SubmoduleImportation.__init__
    def __init__(self, name, source):
        # A dot should only appear in the name when it is a submodule import
        assert '.' in name and (not source or isinstance(source, ast.Import))
        package_name = name.split('.')[0]
        super().__init__(package_name, source)
        self.fullName = name

    #@+node:ekr.20240702085302.38: *4* SubmoduleImportation.redefines
    def redefines(self, other):
        if isinstance(other, Importation):
            return self.fullName == other.fullName
        return super().redefines(other)

    #@+node:ekr.20240702085302.39: *4* SubmoduleImportation.__str__
    def __str__(self):
        return self.fullName

    #@+node:ekr.20240702085302.40: *4* SubmoduleImportation.source_statement
    @property
    def source_statement(self):
        return 'import ' + self.fullName


    #@-others
#@+node:ekr.20240702085302.59: ** checker.py: Scope classes
#@+node:ekr.20240702085302.60: *3*   class Scope(dict)
class Scope(dict):
    importStarred = False       # set to True when import * is found

    def __repr__(self):
        scope_cls = self.__class__.__name__
        return f'<{scope_cls} at 0x{id(self):x} {dict.__repr__(self)}>'


#@+node:ekr.20240702085302.68: *3*  class ModuleScope(Scope)
class ModuleScope(Scope):
    """Scope for a module."""
    _futures_allowed = True
    _annotations_future_enabled = False


#@+node:ekr.20240702085302.61: *3* class ClassScope(Scope)
class ClassScope(Scope):
    pass


#@+node:ekr.20240702085302.69: *3* class DoctestScope(ModuleScope)
class DoctestScope(ModuleScope):
    """Scope for a doctest."""


#@+node:ekr.20240702085302.62: *3* class FunctionScope(Scope)
class FunctionScope(Scope):
    """
    I represent a name scope for a function.

    @ivar globals: Names declared 'global' in this function.
    """
    #@+others
    #@+node:ekr.20240702085302.63: *4* FunctionScope.__init__
    usesLocals = False
    alwaysUsed = {'__tracebackhide__', '__traceback_info__',
                  '__traceback_supplement__', '__debuggerskip__'}

    def __init__(self):
        super().__init__()
        # Simplify: manage the special locals as globals
        self.globals = self.alwaysUsed.copy()
        self.returnValue = None     # First non-empty return

    #@+node:ekr.20240702085302.64: *4* FunctionScope.unused_assignments
    def unused_assignments(self):
        """
        Return a generator for the assignments which have not been used.
        """
        for name, binding in self.items():
            if (not binding.used and
                    name != '_' and  # see issue #202
                    name not in self.globals and
                    not self.usesLocals and
                    isinstance(binding, Assignment)):
                yield name, binding

    #@+node:ekr.20240702085302.65: *4* FunctionScope.unused_annotations
    def unused_annotations(self):
        """
        Return a generator for the annotations which have not been used.
        """
        for name, binding in self.items():
            if not binding.used and isinstance(binding, Annotation):
                yield name, binding


    #@-others
#@+node:ekr.20240702085302.67: *3* class GeneratorScope(Scope)
class GeneratorScope(Scope):
    pass


#@+node:ekr.20240702085302.66: *3* class TypeScope(Scope)
class TypeScope(Scope):
    pass


#@+node:ekr.20240702085302.73: ** checker.py: Typing & Annotations
#@+node:ekr.20240702085302.79: *3* class AnnotationState
class AnnotationState:
    NONE = 0
    STRING = 1
    BARE = 2

#@+node:ekr.20240702085302.77: *3* function: _is_any_typing_member
def _is_any_typing_member(node, scope_stack):
    """
    Determine whether `node` represents any member of a typing module.

    This is used as part of working out whether we are within a type annotation
    context.
    """
    return _is_typing_helper(node, lambda x: True, scope_stack)


#@+node:ekr.20240702085302.76: *3* function: _is_typing
def _is_typing(node, typing_attr, scope_stack):
    """
    Determine whether `node` represents the member of a typing module specified
    by `typing_attr`.

    This is used as part of working out whether we are within a type annotation
    context.
    """
    return _is_typing_helper(node, lambda x: x == typing_attr, scope_stack)


#@+node:ekr.20240702085302.75: *3* function: _is_typing_helper
def _is_typing_helper(node, is_name_match_fn, scope_stack):
    """
    Internal helper to determine whether or not something is a member of a
    typing module. This is used as part of working out whether we are within a
    type annotation context.

    Note: you probably don't want to use this function directly. Instead see the
    utils below which wrap it (`_is_typing` and `_is_any_typing_member`).
    """

    def _bare_name_is_attr(name):
        for scope in reversed(scope_stack):
            if name in scope:
                return (
                    isinstance(scope[name], ImportationFrom) and
                    scope[name].module in TYPING_MODULES and
                    is_name_match_fn(scope[name].real_name)
                )

        return False

    def _module_scope_is_typing(name):
        for scope in reversed(scope_stack):
            if name in scope:
                return (
                    isinstance(scope[name], Importation) and
                    scope[name].fullName in TYPING_MODULES
                )

        return False

    return (
        (
            isinstance(node, ast.Name) and
            _bare_name_is_attr(node.id)
        ) or (
            isinstance(node, ast.Attribute) and
            isinstance(node.value, ast.Name) and
            _module_scope_is_typing(node.value.id) and
            is_name_match_fn(node.attr)
        )
    )


#@+node:ekr.20240702085302.80: *3* function: in_annotation
def in_annotation(func):
    @functools.wraps(func)
    def in_annotation_func(self, *args, **kwargs):
        with self._enter_annotation():
            return func(self, *args, **kwargs)
    return in_annotation_func


#@+node:ekr.20240702085302.81: *3* function: in_string_annotation
def in_string_annotation(func):
    @functools.wraps(func)
    def in_annotation_func(self, *args, **kwargs):
        with self._enter_annotation(AnnotationState.STRING):
            return func(self, *args, **kwargs)
    return in_annotation_func


#@+node:ekr.20240702085302.78: *3* function: is_typing_overload
def is_typing_overload(value, scope_stack):
    return (
        isinstance(value.source, (ast.FunctionDef, ast.AsyncFunctionDef)) and
        any(
            _is_typing(dec, 'overload', scope_stack)
            for dec in value.source.decorator_list
        )
    )


#@+node:ekr.20240702085302.82: ** class Checker
class Checker:
    """I check the cleanliness and sanity of Python code."""

    #@+<< Checker: class data >>
    #@+node:ekr.20240702085302.83: *3* << Checker: class data >>
    _ast_node_scope = {
        ast.Module: ModuleScope,
        ast.ClassDef: ClassScope,
        ast.FunctionDef: FunctionScope,
        ast.AsyncFunctionDef: FunctionScope,
        ast.Lambda: FunctionScope,
        ast.ListComp: GeneratorScope,
        ast.SetComp: GeneratorScope,
        ast.GeneratorExp: GeneratorScope,
        ast.DictComp: GeneratorScope,
    }

    nodeDepth = 0
    offset = None
    _in_annotation = AnnotationState.NONE

    builtIns = set(builtin_vars).union(_MAGIC_GLOBALS)
    _customBuiltIns = os.environ.get('PYFLAKES_BUILTINS')
    if _customBuiltIns:
        builtIns.update(_customBuiltIns.split(','))
    del _customBuiltIns
    #@-<< Checker: class data >>

    #@+others
    #@+node:ekr.20240702085302.84: *3* Checker.__init__
    def __init__(self, tree, filename='(none)', builtins=None, withDoctest='PYFLAKES_DOCTEST' in os.environ):
                     ###, file_tokens=()):
        self._nodeHandlers = {}
        self._deferred = collections.deque()
        self.deadScopes = []
        self.messages = []
        self.filename = filename
        if builtins:
            self.builtIns = self.builtIns.union(builtins)
        if 0:  ###
            g.trace(g.callers())
            # g.printObj(self.builtIns, tag='Checker.builtIns')  ###
        self.withDoctest = withDoctest
        self.exceptHandlers = [()]
        self.root = tree

        self.scopeStack = []
        try:
            scope_tp = Checker._ast_node_scope[type(tree)]
        except KeyError:
            raise RuntimeError('No scope implemented for the node %r' % tree)

        with self.in_scope(scope_tp):
            for builtin in self.builtIns:
                self.addBinding(None, Builtin(builtin))
            self.handleChildren(tree)
            self._run_deferred()

        self.checkDeadScopes()

        ###
            # if file_tokens:
                # warnings.warn(
                    # '`file_tokens` will be removed in a future version',
                    # stacklevel=2,
                # )

    #@+node:ekr.20240702085302.85: *3* Checker: Deferred functions
    #@+node:ekr.20240702085302.86: *4* Checker.deferFunction
    def deferFunction(self, callable):
        """
        Schedule a function handler to be called just before completion.

        This is used for handling function bodies, which must be deferred
        because code later in the file might modify the global scope. When
        `callable` is called, the scope at the time this is called will be
        restored, however it will contain any new bindings added to it.
        """
        self._deferred.append((callable, self.scopeStack[:], self.offset))

    #@+node:ekr.20240702085302.87: *4* Checker._run_deferred
    def _run_deferred(self):
        orig = (self.scopeStack, self.offset)

        while self._deferred:
            handler, scope, offset = self._deferred.popleft()
            self.scopeStack, self.offset = scope, offset
            handler()

        self.scopeStack, self.offset = orig

    #@+node:ekr.20240702085302.88: *3* Checker._in_doctest
    def _in_doctest(self):
        return (len(self.scopeStack) >= 2 and
                isinstance(self.scopeStack[1], DoctestScope))

    #@+node:ekr.20240702085302.89: *3* Checker: Properties
    #@+node:ekr.20240702085302.90: *4* Checker.futuresAllowed
    @property
    def futuresAllowed(self):
        if not all(isinstance(scope, ModuleScope)
                   for scope in self.scopeStack):
            return False

        return self.scope._futures_allowed

    @futuresAllowed.setter
    def futuresAllowed(self, value):
        assert value is False
        if isinstance(self.scope, ModuleScope):
            self.scope._futures_allowed = False

    #@+node:ekr.20240702085302.91: *4* Checker.annotationsFutureEnabled
    @property
    def annotationsFutureEnabled(self):
        scope = self.scopeStack[0]
        if not isinstance(scope, ModuleScope):
            return False
        return scope._annotations_future_enabled

    @annotationsFutureEnabled.setter
    def annotationsFutureEnabled(self, value):
        assert value is True
        assert isinstance(self.scope, ModuleScope)
        self.scope._annotations_future_enabled = True

    #@+node:ekr.20240702085302.92: *4* Checker.scope & in_scope (@contextlib.contextmanager)
    @property
    def scope(self):
        return self.scopeStack[-1]

    @contextlib.contextmanager
    def in_scope(self, cls):
        self.scopeStack.append(cls())
        try:
            yield
        finally:
            self.deadScopes.append(self.scopeStack.pop())

    #@+node:ekr.20240702085302.93: *3* Checker: Utils
    #@+node:ekr.20240702085302.94: *4* Checker.checkDeadScopes
    def checkDeadScopes(self):
        """
        Look at scopes which have been fully examined and report names in them
        which were imported but unused.
        """
        for scope in self.deadScopes:
            # imports in classes are public members
            if isinstance(scope, ClassScope):
                continue

            if isinstance(scope, FunctionScope):
                for name, binding in scope.unused_assignments():
                    self.report(messages.UnusedVariable, binding.source, name)
                for name, binding in scope.unused_annotations():
                    self.report(messages.UnusedAnnotation, binding.source, name)

            all_binding = scope.get('__all__')
            if all_binding and not isinstance(all_binding, ExportBinding):
                all_binding = None

            if all_binding:
                all_names = set(all_binding.names)
                undefined = [
                    name for name in all_binding.names
                    if name not in scope
                ]
            else:
                all_names = undefined = []

            if undefined:
                if not scope.importStarred and \
                   os.path.basename(self.filename) != '__init__.py':
                    # Look for possible mistakes in the export list
                    for name in undefined:
                        self.report(messages.UndefinedExport,
                                    scope['__all__'].source, name)

                # mark all import '*' as used by the undefined in __all__
                if scope.importStarred:
                    from_list = []
                    for binding in scope.values():
                        if isinstance(binding, StarImportation):
                            binding.used = all_binding
                            from_list.append(binding.fullName)
                    # report * usage, with a list of possible sources
                    from_list = ', '.join(sorted(from_list))
                    for name in undefined:
                        self.report(messages.ImportStarUsage,
                                    scope['__all__'].source, name, from_list)

            # Look for imported names that aren't used.
            for value in scope.values():
                if isinstance(value, Importation):
                    used = value.used or value.name in all_names
                    if not used:
                        messg = messages.UnusedImport
                        self.report(messg, value.source, str(value))
                    for node in value.redefined:
                        if isinstance(self.getParent(node), FOR_TYPES):
                            messg = messages.ImportShadowedByLoopVar
                        elif used:
                            continue
                        else:
                            messg = messages.RedefinedWhileUnused
                        self.report(messg, node, value.name, value.source)

    #@+node:ekr.20240702085302.95: *4* Checker.report
    def report(self, messageClass, *args, **kwargs):
        self.messages.append(messageClass(self.filename, *args, **kwargs))

    #@+node:ekr.20240702085302.96: *4* Checker: Tree utils
    #@+node:ekr.20240702085302.97: *5* Checker.getParent
    def getParent(self, node):
        # Lookup the first parent which is not Tuple, List or Starred
        while True:
            node = node._pyflakes_parent
            if not hasattr(node, 'elts') and not hasattr(node, 'ctx'):
                return node

    #@+node:ekr.20240702085302.98: *5* Checker.getCommonAncestor
    def getCommonAncestor(self, lnode, rnode, stop):
        if (
                stop in (lnode, rnode) or
                not (
                    hasattr(lnode, '_pyflakes_parent') and
                    hasattr(rnode, '_pyflakes_parent')
                )
        ):
            return None
        if lnode is rnode:
            return lnode

        if (lnode._pyflakes_depth > rnode._pyflakes_depth):
            return self.getCommonAncestor(lnode._pyflakes_parent, rnode, stop)
        if (lnode._pyflakes_depth < rnode._pyflakes_depth):
            return self.getCommonAncestor(lnode, rnode._pyflakes_parent, stop)
        return self.getCommonAncestor(
            lnode._pyflakes_parent,
            rnode._pyflakes_parent,
            stop,
        )

    #@+node:ekr.20240702085302.99: *5* Checker.descendantOf
    def descendantOf(self, node, ancestors, stop):
        for a in ancestors:
            if self.getCommonAncestor(node, a, stop):
                return True
        return False

    #@+node:ekr.20240702085302.100: *5* Checker._getAncestor
    def _getAncestor(self, node, ancestor_type):
        parent = node
        while True:
            if parent is self.root:
                return None
            parent = self.getParent(parent)
            if isinstance(parent, ancestor_type):
                return parent

    #@+node:ekr.20240702085302.101: *5* Checker.getScopeNode
    def getScopeNode(self, node):
        return self._getAncestor(node, tuple(Checker._ast_node_scope.keys()))

    #@+node:ekr.20240702085302.102: *5* Checker.differentForks
    def differentForks(self, lnode, rnode):
        """True, if lnode and rnode are located on different forks of IF/TRY"""
        ancestor = self.getCommonAncestor(lnode, rnode, self.root)
        parts = getAlternatives(ancestor)
        if parts:
            for items in parts:
                if self.descendantOf(lnode, items, ancestor) ^ \
                   self.descendantOf(rnode, items, ancestor):
                    return True
        return False

    #@+node:ekr.20240702085302.103: *4* Checker.addBinding
    def addBinding(self, node, value):
        """
        Called when a binding is altered.

        - `node` is the statement responsible for the change
        - `value` is the new value, a Binding instance
        """
        # assert value.source in (node, node._pyflakes_parent):
        for scope in self.scopeStack[::-1]:
            if value.name in scope:
                break
        existing = scope.get(value.name)
        ### g.trace(node.__class__.__name__, value)

        if (existing and not isinstance(existing, Builtin) and
                not self.differentForks(node, existing.source)):

            parent_stmt = self.getParent(value.source)
            if isinstance(existing, Importation) and isinstance(parent_stmt, FOR_TYPES):
                self.report(messages.ImportShadowedByLoopVar,
                            node, value.name, existing.source)

            elif scope is self.scope:
                if (
                        (not existing.used and value.redefines(existing)) and
                        (value.name != '_' or isinstance(existing, Importation)) and
                        not is_typing_overload(existing, self.scopeStack)
                ):
                    self.report(messages.RedefinedWhileUnused,
                                node, value.name, existing.source)

            elif isinstance(existing, Importation) and value.redefines(existing):
                existing.redefined.append(node)

        if value.name in self.scope:
            # then assume the rebound name is used as a global or within a loop
            value.used = self.scope[value.name].used

        # don't treat annotations as assignments if there is an existing value
        # in scope
        if value.name not in self.scope or not isinstance(value, Annotation):
            if isinstance(value, NamedExprAssignment):
                # PEP 572: use scope in which outermost generator is defined
                scope = next(
                    scope
                    for scope in reversed(self.scopeStack)
                    if not isinstance(scope, GeneratorScope)
                )
                # it may be a re-assignment to an already existing name
                scope.setdefault(value.name, value)
            else:
                self.scope[value.name] = value

    #@+node:ekr.20240702085302.113: *4* Checker: is*
    #@+node:ekr.20240702085302.114: *5* Checker.isLiteralTupleUnpacking
    def isLiteralTupleUnpacking(self, node):
        if isinstance(node, ast.Assign):
            for child in node.targets + [node.value]:
                if not hasattr(child, 'elts'):
                    return False
            return True

    #@+node:ekr.20240702085302.115: *5* Checker.isDocstring
    def isDocstring(self, node):
        """
        Determine if the given node is a docstring, as long as it is at the
        correct place in the node tree.
        """
        return (
            isinstance(node, ast.Expr) and
            isinstance(node.value, ast.Constant) and
            isinstance(node.value.value, str)
        )

    #@+node:ekr.20240702085302.116: *4* Checker.getDocstring
    def getDocstring(self, node):
        if (
                isinstance(node, ast.Expr) and
                isinstance(node.value, ast.Constant) and
                isinstance(node.value.value, str)
        ):
            return node.value.value, node.lineno - 1
        else:
            return None, None

    #@+node:ekr.20240702110753.1: *3* Checker: Utils for visitors
    #@+node:ekr.20240702085302.110: *4* Checker._enter_annotation
    @contextlib.contextmanager
    def _enter_annotation(self, ann_type=AnnotationState.BARE):
        orig, self._in_annotation = self._in_annotation, ann_type
        try:
            yield
        finally:
            self._in_annotation = orig

    #@+node:ekr.20240702085302.111: *4* Checker._in_postponed_annotation
    @property
    def _in_postponed_annotation(self):
        return (
            self._in_annotation == AnnotationState.STRING or
            self.annotationsFutureEnabled
        )

    #@+node:ekr.20240702085302.157: *4* Checker._type_param_scope (@contextlib.contextmanager)
    @contextlib.contextmanager
    def _type_param_scope(self, node):
        with contextlib.ExitStack() as ctx:
            if sys.version_info >= (3, 12):
                ctx.enter_context(self.in_scope(TypeScope))
                for param in node.type_params:
                    self.handleNode(param, node)
            yield

    #@+node:ekr.20240702085302.104: *4* Checker._unknown_handler
    def _unknown_handler(self, node):
        # this environment variable configures whether to error on unknown
        # ast types.
        #
        # this is silent by default but the error is enabled for the pyflakes
        # testsuite.
        #
        # this allows new syntax to be added to python without *requiring*
        # changes from the pyflakes side.  but will still produce an error
        # in the pyflakes testsuite (so more specific handling can be added if
        # needed).
        if os.environ.get('PYFLAKES_ERROR_UNKNOWN'):
            raise NotImplementedError(f'Unexpected type: {type(node)}')
        else:
            self.handleChildren(node)

    #@+node:ekr.20240702085302.105: *4* Checker.getNodeHandler
    def getNodeHandler(self, node_class):
        try:
            return self._nodeHandlers[node_class]
        except KeyError:
            nodeType = node_class.__name__.upper()
        self._nodeHandlers[node_class] = handler = getattr(
            self, nodeType, self._unknown_handler,
        )
        return handler

    #@+node:ekr.20240702085302.122: *4* Checker.handle_annotation_always_deferred
    def handle_annotation_always_deferred(self, annotation, parent):
        fn = in_annotation(Checker.handleNode)
        self.deferFunction(lambda: fn(self, annotation, parent))

    #@+node:ekr.20240702085302.123: *4* Checker.handleAnnotation
    @in_annotation
    def handleAnnotation(self, annotation, node):
        if (
                isinstance(annotation, ast.Constant) and
                isinstance(annotation.value, str)
        ):
            # Defer handling forward annotation.
            self.deferFunction(functools.partial(
                self.handleStringAnnotation,
                annotation.value,
                node,
                annotation.lineno,
                annotation.col_offset,
                messages.ForwardAnnotationSyntaxError,
            ))
        elif self.annotationsFutureEnabled:
            self.handle_annotation_always_deferred(annotation, node)
        else:
            self.handleNode(annotation, node)

    #@+node:ekr.20240702085302.112: *4* Checker.handleChildren & synonyms (changed)
    def handleChildren(self, tree, omit=None):
        """Do not call handleChildren if the order of visiting fields matters!"""
        for field in tree.__class__._fields:
            if omit and field in omit:
                ### g.trace(f"{g.callers(1):>14} {field:>12} {omit!r}")
                continue
            node = getattr(tree, field, None)
            if isinstance(node, ast.AST):
                self.handleNode(node, tree) 
            elif isinstance(node, list):
                for item in node:
                    if isinstance(item, ast.AST):
                        self.handleNode(item, tree) 
            
    # "stmt" type nodes.
    MODULE = handleChildren
    DELETE = WHILE = WITH = WITHITEM = ASYNCWITH = EXPR = handleChildren

    # "expr" type nodes
    BOOLOP = UNARYOP = SET = STARRED = NAMECONSTANT = handleChildren

    # "match" type nodes.
    MATCH = MATCH_CASE = MATCHCLASS = MATCHOR = MATCHSEQUENCE = handleChildren
    MATCHSINGLETON = MATCHVALUE = handleChildren

    # "slice" type nodes.
    SLICE = EXTSLICE = INDEX = handleChildren
    #@+node:ekr.20240702085302.120: *4* Checker.handleDoctests
    _getDoctestExamples = doctest.DocTestParser().get_examples

    def handleDoctests(self, node):
        try:
            (docstring, node_lineno) = self.getDocstring(node.body[0])
            examples = docstring and self._getDoctestExamples(docstring)
        except (ValueError, IndexError):
            # e.g. line 6 of the docstring for <string> has inconsistent
            # leading whitespace: ...
            return
        if not examples:
            return

        # Place doctest in module scope
        saved_stack = self.scopeStack
        self.scopeStack = [self.scopeStack[0]]
        node_offset = self.offset or (0, 0)
        with self.in_scope(DoctestScope):
            if '_' not in self.scopeStack[0]:
                self.addBinding(None, Builtin('_'))
            for example in examples:
                try:
                    tree = ast.parse(example.source, "<doctest>")
                except SyntaxError as e:
                    position = (node_lineno + example.lineno + e.lineno,
                                example.indent + 4 + (e.offset or 0))
                    self.report(messages.DoctestSyntaxError, node, position)
                else:
                    self.offset = (node_offset[0] + node_lineno + example.lineno,
                                   node_offset[1] + example.indent + 4)
                    self.handleChildren(tree)
                    self.offset = node_offset
        self.scopeStack = saved_stack

    #@+node:ekr.20240702085302.119: *4* Checker.handleNode & synonyms
    def handleNode(self, node, parent):
        if node is None:
            return
        if self.offset and getattr(node, 'lineno', None) is not None:
            node.lineno += self.offset[0]
            node.col_offset += self.offset[1]
        if (
                self.futuresAllowed and
                self.nodeDepth == 0 and
                not isinstance(node, ast.ImportFrom) and
                not self.isDocstring(node)
        ):
            self.futuresAllowed = False
        self.nodeDepth += 1
        node._pyflakes_depth = self.nodeDepth
        node._pyflakes_parent = parent
        try:
            handler = self.getNodeHandler(node.__class__)
            handler(node)
        finally:
            self.nodeDepth -= 1

    #@+node:ekr.20240702085302.121: *4* Checker.handleStringAnnotation
    @in_string_annotation
    def handleStringAnnotation(self, s, node, ref_lineno, ref_col_offset, err):
        try:
            tree = ast.parse(s)
        except SyntaxError:
            self.report(err, node, s)
            return

        body = tree.body
        if len(body) != 1 or not isinstance(body[0], ast.Expr):
            self.report(err, node, s)
            return

        parsed_annotation = tree.body[0].value
        for descendant in ast.walk(parsed_annotation):
            if (
                    'lineno' in descendant._attributes and
                    'col_offset' in descendant._attributes
            ):
                descendant.lineno = ref_lineno
                descendant.col_offset = ref_col_offset

        self.handleNode(parsed_annotation, node)

    #@+node:ekr.20240702085302.106: *4* Checker: handleNodeLoad/Store/Delete
    #@+node:ekr.20240702085302.107: *5* Checker.handleNodeLoad
    def handleNodeLoad(self, node, parent):
        name = getNodeName(node)
        if not name:
            return

        # only the following can access class scoped variables (since classes
        # aren't really a scope)
        # - direct accesses (not within a nested scope)
        # - generators
        # - type annotations (for generics, etc.)
        can_access_class_vars = None
        importStarred = None

        # try enclosing function scopes and global scope
        for scope in self.scopeStack[-1::-1]:
            if isinstance(scope, ClassScope):
                if name == '__class__':
                    return
                elif can_access_class_vars is False:
                    # only generators used in a class scope can access the
                    # names of the class. this is skipped during the first
                    # iteration
                    continue

            binding = scope.get(name, None)
            if isinstance(binding, Annotation) and not self._in_postponed_annotation:
                scope[name].used = (self.scope, node)
                continue

            if name == 'print' and isinstance(binding, Builtin):
                if (isinstance(parent, ast.BinOp) and
                        isinstance(parent.op, ast.RShift)):
                    self.report(messages.InvalidPrintSyntax, node)

            try:
                scope[name].used = (self.scope, node)

                # if the name of SubImportation is same as
                # alias of other Importation and the alias
                # is used, SubImportation also should be marked as used.
                n = scope[name]
                if isinstance(n, Importation) and n._has_alias():
                    try:
                        scope[n.fullName].used = (self.scope, node)
                    except KeyError:
                        pass
            except KeyError:
                pass
            else:
                return

            importStarred = importStarred or scope.importStarred

            if can_access_class_vars is not False:
                can_access_class_vars = isinstance(
                    scope, (TypeScope, GeneratorScope),
                )

        if importStarred:
            from_list = []

            for scope in self.scopeStack[-1::-1]:
                for binding in scope.values():
                    if isinstance(binding, StarImportation):
                        # mark '*' imports as used for each scope
                        binding.used = (self.scope, node)
                        from_list.append(binding.fullName)

            # report * usage, with a list of possible sources
            from_list = ', '.join(sorted(from_list))
            self.report(messages.ImportStarUsage, node, name, from_list)
            return

        if name == '__path__' and os.path.basename(self.filename) == '__init__.py':
            # the special name __path__ is valid only in packages
            return

        if name in DetectClassScopedMagic.names and isinstance(self.scope, ClassScope):
            return

        # protected with a NameError handler?
        if 'NameError' not in self.exceptHandlers[-1]:
            self.report(messages.UndefinedName, node, name)

    #@+node:ekr.20240702085302.108: *5* Checker.handleNodeStore
    def handleNodeStore(self, node):
        name = getNodeName(node)
        if not name:
            return
        # if the name hasn't already been defined in the current scope
        if isinstance(self.scope, FunctionScope) and name not in self.scope:
            # for each function or module scope above us
            for scope in self.scopeStack[:-1]:
                if not isinstance(scope, (FunctionScope, ModuleScope)):
                    continue
                # if the name was defined in that scope, and the name has
                # been accessed already in the current scope, and hasn't
                # been declared global
                used = name in scope and scope[name].used
                if used and used[0] is self.scope and name not in self.scope.globals:
                    # then it's probably a mistake
                    self.report(messages.UndefinedLocal,
                                scope[name].used[1], name, scope[name].source)
                    break

        parent_stmt = self.getParent(node)
        if isinstance(parent_stmt, ast.AnnAssign) and parent_stmt.value is None:
            binding = Annotation(name, node)
        elif (
            isinstance(parent_stmt, (FOR_TYPES, ast.comprehension))
            or (
                parent_stmt != node._pyflakes_parent
                and not self.isLiteralTupleUnpacking(parent_stmt)
            )
        ):
            binding = Binding(name, node)
        elif (
            name == '__all__'
            and isinstance(self.scope, ModuleScope)
            and isinstance(node._pyflakes_parent, (ast.Assign, ast.AugAssign, ast.AnnAssign))
        ):
            binding = ExportBinding(name, node._pyflakes_parent, self.scope)
        elif isinstance(parent_stmt, ast.NamedExpr):
            binding = NamedExprAssignment(name, node)
        else:
            binding = Assignment(name, node)
        self.addBinding(node, binding)

    #@+node:ekr.20240702085302.109: *5* Checker.handleNodeDelete
    def handleNodeDelete(self, node):

        def on_conditional_branch():
            """
            Return `True` if node is part of a conditional body.
            """
            current = getattr(node, '_pyflakes_parent', None)
            while current:
                if isinstance(current, (ast.If, ast.While, ast.IfExp)):
                    return True
                current = getattr(current, '_pyflakes_parent', None)
            return False

        name = getNodeName(node)
        if not name:
            return

        if on_conditional_branch():
            # We cannot predict if this conditional branch is going to
            # be executed.
            return

        if isinstance(self.scope, FunctionScope) and name in self.scope.globals:
            self.scope.globals.remove(name)
        else:
            try:
                del self.scope[name]
            except KeyError:
                self.report(messages.UndefinedName, node, name)

    #@+node:ekr.20240702085302.117: *3* Checker: Visitors
    #@+node:ekr.20240702085302.154: *4* Checker.ANNASSIGN
    def ANNASSIGN(self, node):
        self.handleAnnotation(node.annotation, node)
        # If the assignment has value, handle the *value* now.
        if node.value:
            # If the annotation is `TypeAlias`, handle the *value* as an annotation.
            if _is_typing(node.annotation, 'TypeAlias', self.scopeStack):
                self.handleAnnotation(node.value, node)
            else:
                self.handleNode(node.value, node)
        self.handleNode(node.target, node)

    #@+node:ekr.20240702085302.146: *4* Checker.ARG
    def ARG(self, node):
        self.addBinding(node, Argument(node.arg, self.getScopeNode(node)))

    #@+node:ekr.20240702085302.145: *4* Checker.ARGUMENTS (changed)
    def ARGUMENTS(self, node):
        # EKR: Unit tests fail w/o these omissions.
        ### g.trace(g.callers(2), node.__class__.__name__)
        self.handleChildren(node, omit=('defaults', 'kw_defaults'))
    #@+node:ekr.20240702085302.136: *4* Checker.ASSERT
    def ASSERT(self, node):
        if isinstance(node.test, ast.Tuple) and node.test.elts != []:
            self.report(messages.AssertTuple, node)
        self.handleChildren(node)

    #@+node:ekr.20240704151835.1: *4* Checker.ASSIGN  (new)
    def ASSIGN(self, node):

        # Order matters.
        value = getattr(node, 'value', None)
        targets = getattr(node, 'targets', [])
        # type_comment = getattr(node, 'type_comment', None)
        self.handleNode(value, node)  # Value first.
        for target in targets:
            self.handleNode(target, node)
        # self.handleNode(type_comment, node)
    #@+node:ekr.20240704165918.1: *4* Checker.ATTRIBUTE (new)
    def ATTRIBUTE(self, node):
        
        # Faster than handleChildren.
        # attr is a string.
        value = getattr(node, 'value', None)
        self.handleNode(value, node)
    #@+node:ekr.20240702085302.148: *4* Checker.AUGASSIGN
    def AUGASSIGN(self, node):
        self.handleNodeLoad(node.target, node)
        self.handleNode(node.value, node)
        self.handleNode(node.target, node)

    #@+node:ekr.20240702085302.129: *4* Checker.BINOP & helper
    def BINOP(self, node):
        if (
                isinstance(node.op, ast.Mod) and
                isinstance(node.left, ast.Constant) and
                isinstance(node.left.value, str)
        ):
            self._handle_percent_format(node)
        self.handleChildren(node)

    #@+node:ekr.20240702085302.128: *5* Checker._handle_percent_format
    def _handle_percent_format(self, node):
        try:
            placeholders = parse_percent_format(node.left.value)
        except ValueError:
            self.report(
                messages.PercentFormatInvalidFormat,
                node,
                'incomplete format',
            )
            return

        named = set()
        positional_count = 0
        positional = None
        for _, placeholder in placeholders:
            if placeholder is None:
                continue
            name, _, width, precision, conversion = placeholder

            if conversion == '%':
                continue

            if conversion not in VALID_CONVERSIONS:
                self.report(
                    messages.PercentFormatUnsupportedFormatCharacter,
                    node,
                    conversion,
                )

            if positional is None and conversion:
                positional = name is None

            for part in (width, precision):
                if part is not None and '*' in part:
                    if not positional:
                        self.report(
                            messages.PercentFormatStarRequiresSequence,
                            node,
                        )
                    else:
                        positional_count += 1

            if positional and name is not None:
                self.report(
                    messages.PercentFormatMixedPositionalAndNamed,
                    node,
                )
                return
            elif not positional and name is None:
                self.report(
                    messages.PercentFormatMixedPositionalAndNamed,
                    node,
                )
                return

            if positional:
                positional_count += 1
            else:
                named.add(name)

        if (
                isinstance(node.right, (ast.List, ast.Tuple)) and
                # does not have any *splats (py35+ feature)
                not any(
                    isinstance(elt, ast.Starred)
                    for elt in node.right.elts
                )
        ):
            substitution_count = len(node.right.elts)
            if positional and positional_count != substitution_count:
                self.report(
                    messages.PercentFormatPositionalCountMismatch,
                    node,
                    positional_count,
                    substitution_count,
                )
            elif not positional:
                self.report(messages.PercentFormatExpectedMapping, node)

        if (
                isinstance(node.right, ast.Dict) and
                all(
                    isinstance(k, ast.Constant) and isinstance(k.value, str)
                    for k in node.right.keys
                )
        ):
            if positional and positional_count > 1:
                self.report(messages.PercentFormatExpectedSequence, node)
                return

            substitution_keys = {k.value for k in node.right.keys}
            extra_keys = substitution_keys - named
            missing_keys = named - substitution_keys
            if not positional and extra_keys:
                self.report(
                    messages.PercentFormatExtraNamedArguments,
                    node,
                    ', '.join(sorted(extra_keys)),
                )
            if not positional and missing_keys:
                self.report(
                    messages.PercentFormatMissingArgument,
                    node,
                    ', '.join(sorted(missing_keys)),
                )

    #@+node:ekr.20240702085302.127: *4* Checker.CALL & helper (Changed)
    def CALL(self, node):
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Constant)
            and isinstance(node.func.value.value, str)
            and node.func.attr == 'format'
        ):
            self._handle_string_dot_format(node)
            
        def do_call_children(node2, omit=None):
            # Call(expr func, expr* args, keyword* keywords)
            ### g.trace(f"{node2.__class__.__name__:>12} {omit!r}") #  {g.callers(2)}")
            self.handleChildren(node2, omit=omit)

        omit = []
        annotated = []
        not_annotated = []

        if len(node.args) >= 1 and _is_typing(node.func, 'cast', self.scopeStack):
            with self._enter_annotation():
                self.handleNode(node.args[0], node)

        elif _is_typing(node.func, 'TypeVar', self.scopeStack):

            # TypeVar("T", "int", "str")
            omit += ["args"]
            annotated += [arg for arg in node.args[1:]]

            # TypeVar("T", bound="str")
            omit += ["keywords"]
            annotated += [k.value for k in node.keywords if k.arg == "bound"]
            not_annotated += [
                (k, ["value"] if k.arg == "bound" else None)
                for k in node.keywords
            ]

        elif _is_typing(node.func, "TypedDict", self.scopeStack):
            # TypedDict("a", {"a": int})
            if len(node.args) > 1 and isinstance(node.args[1], ast.Dict):
                omit += ["args"]
                annotated += node.args[1].values
                not_annotated += [
                    (arg, ["values"] if i == 1 else None)
                    for i, arg in enumerate(node.args)
                ]

            # TypedDict("a", a=int)
            omit += ["keywords"]
            annotated += [k.value for k in node.keywords]
            not_annotated += [(k, ["value"]) for k in node.keywords]

        elif _is_typing(node.func, "NamedTuple", self.scopeStack):
            # NamedTuple("a", [("a", int)])
            if (
                len(node.args) > 1 and
                isinstance(node.args[1], (ast.Tuple, ast.List)) and
                all(isinstance(x, (ast.Tuple, ast.List)) and
                    len(x.elts) == 2 for x in node.args[1].elts)
            ):
                omit += ["args"]
                annotated += [elt.elts[1] for elt in node.args[1].elts]
                not_annotated += [(elt.elts[0], None) for elt in node.args[1].elts]
                not_annotated += [
                    (arg, ["elts"] if i == 1 else None)
                    for i, arg in enumerate(node.args)
                ]
                not_annotated += [(elt, "elts") for elt in node.args[1].elts]

            # NamedTuple("a", a=int)
            omit += ["keywords"]
            annotated += [k.value for k in node.keywords]
            not_annotated += [(k, ["value"]) for k in node.keywords]

        if omit:
            with self._enter_annotation(AnnotationState.NONE):
                for na_node, na_omit in not_annotated:
                    ### self.handleChildren(na_node, omit=na_omit)
                    do_call_children(na_node, omit=na_omit)
                ### self.handleChildren(node, omit=omit)
                do_call_children(node, omit=omit)

            with self._enter_annotation():
                for annotated_node in annotated:
                    self.handleNode(annotated_node, node)
        else:
            ### self.handleChildren(node)
            do_call_children(node)
    #@+node:ekr.20240702085302.126: *5* Checker._handle_string_dot_format
    def _handle_string_dot_format(self, node):
        try:
            placeholders = tuple(parse_format_string(node.func.value.value))
        except ValueError as e:
            self.report(messages.StringDotFormatInvalidFormat, node, e)
            return

        auto = None
        next_auto = 0

        placeholder_positional = set()
        placeholder_named = set()

        def _add_key(fmtkey):
            """Returns True if there is an error which should early-exit"""
            nonlocal auto, next_auto

            if fmtkey is None:  # end of string or `{` / `}` escapes
                return False

            # attributes / indices are allowed in `.format(...)`
            fmtkey, _, _ = fmtkey.partition('.')
            fmtkey, _, _ = fmtkey.partition('[')

            try:
                fmtkey = int(fmtkey)
            except ValueError:
                pass
            else:  # fmtkey was an integer
                if auto is True:
                    self.report(messages.StringDotFormatMixingAutomatic, node)
                    return True
                else:
                    auto = False

            if fmtkey == '':
                if auto is False:
                    self.report(messages.StringDotFormatMixingAutomatic, node)
                    return True
                else:
                    auto = True

                fmtkey = next_auto
                next_auto += 1

            if isinstance(fmtkey, int):
                placeholder_positional.add(fmtkey)
            else:
                placeholder_named.add(fmtkey)

            return False

        for _, fmtkey, spec, _ in placeholders:
            if _add_key(fmtkey):
                return

            # spec can also contain format specifiers
            if spec is not None:
                try:
                    spec_placeholders = tuple(parse_format_string(spec))
                except ValueError as e:
                    self.report(messages.StringDotFormatInvalidFormat, node, e)
                    return

                for _, spec_fmtkey, spec_spec, _ in spec_placeholders:
                    # can't recurse again
                    if spec_spec is not None and '{' in spec_spec:
                        self.report(
                            messages.StringDotFormatInvalidFormat,
                            node,
                            'Max string recursion exceeded',
                        )
                        return
                    if _add_key(spec_fmtkey):
                        return

        # bail early if there is *args or **kwargs
        if (
                # *args
                any(isinstance(arg, ast.Starred) for arg in node.args) or
                # **kwargs
                any(kwd.arg is None for kwd in node.keywords)
        ):
            return

        substitution_positional = set(range(len(node.args)))
        substitution_named = {kwd.arg for kwd in node.keywords}

        extra_positional = substitution_positional - placeholder_positional
        extra_named = substitution_named - placeholder_named

        missing_arguments = (
            (placeholder_positional | placeholder_named) -
            (substitution_positional | substitution_named)
        )

        if extra_positional:
            self.report(
                messages.StringDotFormatExtraPositionalArguments,
                node,
                ', '.join(sorted(str(x) for x in extra_positional)),
            )
        if extra_named:
            self.report(
                messages.StringDotFormatExtraNamedArguments,
                node,
                ', '.join(sorted(extra_named)),
            )
        if missing_arguments:
            self.report(
                messages.StringDotFormatMissingArgument,
                node,
                ', '.join(sorted(str(x) for x in missing_arguments)),
            )

    #@+node:ekr.20240702085302.147: *4* Checker.CLASSDEF
    def CLASSDEF(self, node):
        """
        Check names used in a class definition, including its decorators, base
        classes, and the body of its definition.  Additionally, add its name to
        the current scope.
        """
        for deco in node.decorator_list:
            self.handleNode(deco, node)

        with self._type_param_scope(node):
            for baseNode in node.bases:
                self.handleNode(baseNode, node)
            for keywordNode in node.keywords:
                self.handleNode(keywordNode, node)
            with self.in_scope(ClassScope):
                # doctest does not process doctest within a doctest
                # classes within classes are processed.
                if (self.withDoctest and
                        not self._in_doctest() and
                        not isinstance(self.scope, FunctionScope)):
                    self.deferFunction(lambda: self.handleDoctests(node))
                for stmt in node.body:
                    self.handleNode(stmt, node)

        self.addBinding(node, ClassDefinition(node.name, node))

    #@+node:ekr.20240702085302.155: *4* Checker.COMPARE
    def COMPARE(self, node):
        left = node.left
        for op, right in zip(node.ops, node.comparators):
            if (
                    isinstance(op, (ast.Is, ast.IsNot)) and (
                        _is_const_non_singleton(left) or
                        _is_const_non_singleton(right)
                    )
            ):
                self.report(messages.IsLiteral, node)
            left = right

        self.handleChildren(node)

    #@+node:ekr.20240705064837.1: *4* Checker.COMPREHENSION (new)
    def COMPREHENSION(self, node):

        # Order matters.
        for field in ('iter', 'target'):  # iter first.
            child = getattr(node, field, None)
            self.handleNode(child, node)
        if_statements = getattr(node, 'ifs', [])
        for if_statement in if_statements:
            self.handleNode(if_statement, node)
    #@+node:ekr.20240702085302.130: *4* Checker.CONSTANT & related operators
    def CONSTANT(self, node):
        if isinstance(node.value, str) and self._in_annotation:
            fn = functools.partial(
                self.handleStringAnnotation,
                node.value,
                node,
                node.lineno,
                node.col_offset,
                messages.ForwardAnnotationSyntaxError,
            )
            self.deferFunction(fn)

    #@+node:ekr.20240702085302.140: *4* Checker.CONTINUE & BREAK
    def CONTINUE(self, node):
        # Walk the tree up until we see a loop (OK), a function or class
        # definition (not OK), for 'continue', a finally block (not OK), or
        # the top module scope (not OK)
        n = node
        while hasattr(n, '_pyflakes_parent'):
            n, n_child = n._pyflakes_parent, n
            if isinstance(n, (ast.While, ast.For, ast.AsyncFor)):
                # Doesn't apply unless it's in the loop itself
                if n_child not in n.orelse:
                    return
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                break
        if isinstance(node, ast.Continue):
            self.report(messages.ContinueOutsideLoop, node)
        else:  # ast.Break
            self.report(messages.BreakOutsideLoop, node)

    BREAK = CONTINUE

    #@+node:ekr.20240702085302.134: *4* Checker.DICT
    def DICT(self, node):
        # Complain if there are duplicate keys with different values
        # If they have the same value it's not going to cause potentially
        # unexpected behaviour so we'll not complain.
        keys = [
            convert_to_value(key) for key in node.keys
        ]

        key_counts = collections.Counter(keys)
        duplicate_keys = [
            key for key, count in key_counts.items()
            if count > 1
        ]

        for key in duplicate_keys:
            key_indices = [i for i, i_key in enumerate(keys) if i_key == key]

            values = collections.Counter(
                convert_to_value(node.values[index])
                for index in key_indices
            )
            if any(count == 1 for value, count in values.items()):
                for key_index in key_indices:
                    key_node = node.keys[key_index]
                    if isinstance(key, VariableKey):
                        self.report(messages.MultiValueRepeatedKeyVariable,
                                    key_node,
                                    key.name)
                    else:
                        self.report(
                            messages.MultiValueRepeatedKeyLiteral,
                            key_node,
                            key,
                        )
        self.handleChildren(node)

    #@+node:ekr.20240702085302.153: *4* Checker.EXCEPTHANDLER
    def EXCEPTHANDLER(self, node):
        if node.name is None:
            self.handleChildren(node)
            return

        # If the name already exists in the scope, modify state of existing
        # binding.
        if node.name in self.scope:
            self.handleNodeStore(node)

        # 3.x: the name of the exception, which is not a Name node, but a
        # simple string, creates a local that is only bound within the scope of
        # the except: block. As such, temporarily remove the existing binding
        # to more accurately determine if the name is used in the except:
        # block.

        try:
            prev_definition = self.scope.pop(node.name)
        except KeyError:
            prev_definition = None

        self.handleNodeStore(node)
        self.handleChildren(node)

        # See discussion on https://github.com/PyCQA/pyflakes/pull/59

        # We're removing the local name since it's being unbound after leaving
        # the except: block and it's always unbound if the except: block is
        # never entered. This will cause an "undefined name" error raised if
        # the checked code tries to use the name afterwards.
        #
        # Unless it's been removed already. Then do nothing.

        try:
            binding = self.scope.pop(node.name)
        except KeyError:
            pass
        else:
            if not binding.used:
                self.report(messages.UnusedVariable, node, node.name)

        # Restore.
        if prev_definition:
            self.scope[node.name] = prev_definition

    #@+node:ekr.20240704150603.1: *4* Checker.FOR & ASYNCFOR  (new) 
    def FOR(self, tree):
        
        # Order matters.
        for field in ('iter', 'target', 'type_comment'):
            node = getattr(tree, field, None)
            self.handleNode(node, tree)
        for field in ('body', 'orelse'):
            node =  getattr(tree, field, [])
            for z in node:
                self.handleNode(z, tree)

    ASYNCFOR = FOR
    #@+node:ekr.20240705070528.1: *4* Checker.FORMATTEDVALUE (new)
    def FORMATTEDVALUE(self, node):
        
        # Faster than handleChildren.
        # node.conversion is an int.
        for field in ('value', 'format_spec'):
            child = getattr(node, field, None)
            self.handleNode(child, node)
    #@+node:ekr.20240702085302.143: *4* Checker.FUNCTIONDEF & ASYNCFUNCTIONDEF
    def FUNCTIONDEF(self, node):
        for deco in node.decorator_list:
            self.handleNode(deco, node)

        with self._type_param_scope(node):
            self.LAMBDA(node)

        self.addBinding(node, FunctionDefinition(node.name, node))
        # doctest does not process doctest within a doctest,
        # or in nested functions.
        if (self.withDoctest and
                not self._in_doctest() and
                not isinstance(self.scope, FunctionScope)):
            self.deferFunction(lambda: self.handleDoctests(node))

    ASYNCFUNCTIONDEF = FUNCTIONDEF

    #@+node:ekr.20240702085302.138: *4* Checker.GENERATOREXP, DICTCOMP, LISTCOMP, SETCOMP(changed)
    def GENERATOREXP(self, node):
        with self.in_scope(GeneratorScope):
            generators = getattr(node, 'generators', [])
            elt = getattr(node, 'elt', None)
            for generator in generators:
                self.handleNode(generator, node)
            self.handleNode(elt, node) 

    LISTCOMP = SETCOMP = GENERATOREXP

    if 0:  # Legacy.
        DICTCOMP = GENERATOREXP
    else:  # Works.

        def DICTCOMP(self, node):
            with self.in_scope(GeneratorScope):
                generators = getattr(node, 'generators', [])
                key = getattr(node, 'key', None)
                value = getattr(node, 'value', None)
                for generator in generators:  # generators first.
                    self.handleNode(generator, node)
                self.handleNode(key, node)
                self.handleNode(value, node)
    #@+node:ekr.20240702085302.137: *4* Checker.GLOBAL & NONLOCAL
    def GLOBAL(self, node):
        """
        Keep track of globals declarations.
        """
        global_scope_index = 1 if self._in_doctest() else 0
        global_scope = self.scopeStack[global_scope_index]

        # Ignore 'global' statement in global scope.
        if self.scope is not global_scope:

            # One 'global' statement can bind multiple (comma-delimited) names.
            for node_name in node.names:
                node_value = Assignment(node_name, node)

                # Remove UndefinedName messages already reported for this name.
                # TODO: if the global is not used in this scope, it does not
                # become a globally defined name.  See test_unused_global.
                self.messages = [
                    m for m in self.messages if not
                    isinstance(m, messages.UndefinedName) or
                    m.message_args[0] != node_name]

                # Bind name to global scope if it doesn't exist already.
                global_scope.setdefault(node_name, node_value)

                # Bind name to non-global scopes, but as already "used".
                node_value.used = (global_scope, node)
                for scope in self.scopeStack[global_scope_index + 1:]:
                    scope[node_name] = node_value

    NONLOCAL = GLOBAL

    #@+node:ekr.20240702085302.135: *4* Checker.IF & IFEXPR
    def IF(self, node):
        if isinstance(node.test, ast.Tuple) and node.test.elts != []:
            self.report(messages.IfTuple, node)
        self.handleChildren(node)

    IFEXP = IF

    #@+node:ekr.20240702085302.124: *4* Checker.ignore
    def ignore(self, node):
        pass

    PASS = ignore

    # expression contexts are node instances too, though being constants
    LOAD = STORE = DEL = AUGLOAD = AUGSTORE = PARAM = ignore

    # same for operators
    AND = OR = ADD = SUB = MULT = DIV = MOD = POW = LSHIFT = RSHIFT = \
        BITOR = BITXOR = BITAND = FLOORDIV = INVERT = NOT = UADD = USUB = \
        EQ = NOTEQ = LT = LTE = GT = GTE = IS = ISNOT = IN = NOTIN = \
        MATMULT = ignore
    #@+node:ekr.20240702085302.150: *4* Checker.IMPORT
    def IMPORT(self, node):
        for alias in node.names:
            if '.' in alias.name and not alias.asname:
                importation = SubmoduleImportation(alias.name, node)
            else:
                name = alias.asname or alias.name
                importation = Importation(name, node, alias.name)
            self.addBinding(node, importation)

    #@+node:ekr.20240702085302.151: *4* Checker.IMPORTFROM
    def IMPORTFROM(self, node):
        if node.module == '__future__':
            if not self.futuresAllowed:
                self.report(messages.LateFutureImport, node)
        else:
            self.futuresAllowed = False

        module = ('.' * node.level) + (node.module or '')

        for alias in node.names:
            name = alias.asname or alias.name
            if node.module == '__future__':
                importation = FutureImportation(name, node, self.scope)
                if alias.name not in __future__.all_feature_names:
                    self.report(messages.FutureFeatureNotDefined,
                                node, alias.name)
                if alias.name == 'annotations':
                    self.annotationsFutureEnabled = True
            elif alias.name == '*':
                if not isinstance(self.scope, ModuleScope):
                    self.report(messages.ImportStarNotPermitted,
                                node, module)
                    continue

                self.scope.importStarred = True
                self.report(messages.ImportStarUsed, node, module)
                importation = StarImportation(module, node)
            else:
                importation = ImportationFrom(name, node,
                                              module, alias.name)
            self.addBinding(node, importation)

    #@+node:ekr.20240704160233.1: *4* Checker.KEYWORD (new)
    def KEYWORD(self, node):
        
        # Faster than handle_Children.
        # node.arg is a string.
        child = getattr(node, 'value', None)
        self.handleNode(child, node)

    #@+node:ekr.20240702085302.133: *4* Checker.JOINEDSTR
    _in_fstring = False

    def JOINEDSTR(self, node):
        if (
                # the conversion / etc. flags are parsed as f-strings without
                # placeholders
                not self._in_fstring and
                not any(isinstance(x, ast.FormattedValue) for x in node.values)
        ):
            self.report(messages.FStringMissingPlaceholders, node)

        self._in_fstring, orig = True, self._in_fstring
        try:
            self.handleChildren(node)
        finally:
            self._in_fstring = orig

    #@+node:ekr.20240702085302.144: *4* Checker.LAMBDA & runFunction (unchanged)
    def LAMBDA(self, node):
        args = []
        annotations = []

        for arg in node.args.posonlyargs:
            args.append(arg.arg)
            annotations.append(arg.annotation)
        for arg in node.args.args + node.args.kwonlyargs:
            args.append(arg.arg)
            annotations.append(arg.annotation)
        defaults = node.args.defaults + node.args.kw_defaults

        has_annotations = not isinstance(node, ast.Lambda)

        for arg_name in ('vararg', 'kwarg'):
            wildcard = getattr(node.args, arg_name)
            if not wildcard:
                continue
            args.append(wildcard.arg)
            if has_annotations:
                annotations.append(wildcard.annotation)

        if has_annotations:
            annotations.append(node.returns)

        if len(set(args)) < len(args):
            for (idx, arg) in enumerate(args):
                if arg in args[:idx]:
                    self.report(messages.DuplicateArgument, node, arg)

        for annotation in annotations:
            self.handleAnnotation(annotation, node)

        for default in defaults:
            self.handleNode(default, node)

        def runFunction():
            with self.in_scope(FunctionScope):
                ### g.trace(node.__class__.__name__)
                if 1:  # Legacy.
                    self.handleChildren(
                        node,
                        omit=('decorator_list', 'returns', 'type_params'),
                    )
                else:
                    args = getattr(node, 'args', [])
                    body = getattr(node, 'body', None)
                    for arg in args:
                        self.handleNode(arg, node)
                    self.handleNode(body, node)

        self.deferFunction(runFunction)

    #@+node:ekr.20240702085302.156: *4* Checker.MATCH* & _match_target
    def _match_target(self, node):
        self.handleNodeStore(node)
        self.handleChildren(node)

    MATCHAS = MATCHMAPPING = MATCHSTAR = _match_target

    #@+node:ekr.20240702085302.139: *4* Checker.NAME
    def NAME(self, node):
        """
        Handle occurrence of Name (which can be a load/store/delete access.)
        """
        # Locate the name in locals / function / globals scopes.
        if isinstance(node.ctx, ast.Load):
            self.handleNodeLoad(node, self.getParent(node))
            if (
                node.id == 'locals'
                and isinstance(self.scope, FunctionScope)
                and isinstance(node._pyflakes_parent, ast.Call)
            ):
                # we are doing locals() call in current scope
                self.scope.usesLocals = True
        elif isinstance(node.ctx, ast.Store):
            self.handleNodeStore(node)
        elif isinstance(node.ctx, ast.Del):
            self.handleNodeDelete(node)
        else:
            # Unknown context
            raise RuntimeError(f"Got impossible expression context: {node.ctx!r}")

    #@+node:ekr.20240704160940.1: *4* Checker.NAMEDEXPR (new)
    def NAMEDEXPR(self, node):
        
        # Order matters.
        for field in ('value', 'target'):
            child = getattr(node, field, None)
            self.handleNode(child, node)
    #@+node:ekr.20240702085302.131: *4* Checker.RAISE
    def RAISE(self, node):
        self.handleChildren(node)

        arg = node.exc

        if isinstance(arg, ast.Call):
            if is_notimplemented_name_node(arg.func):
                # Handle "raise NotImplemented(...)"
                self.report(messages.RaiseNotImplemented, node)
        elif is_notimplemented_name_node(arg):
            # Handle "raise NotImplemented"
            self.report(messages.RaiseNotImplemented, node)

    #@+node:ekr.20240702085302.141: *4* Checker.RETURN
    def RETURN(self, node):
        if isinstance(self.scope, (ClassScope, ModuleScope)):
            self.report(messages.ReturnOutsideFunction, node)
            return

        if (
            node.value and
            hasattr(self.scope, 'returnValue') and
            not self.scope.returnValue
        ):
            self.scope.returnValue = node.value
        self.handleNode(node.value, node)

    #@+node:ekr.20240702085302.125: *4* Checker.SUBSCRIPT (changed)
    def SUBSCRIPT(self, node):
     
        def do_subscript():
            # Faster than handleChildren.
            for field in ('value', 'slice'):
                child = getattr(node, field, None)
                self.handleNode(child, node)

        if _is_name_or_attr(node.value, 'Literal'):
            with self._enter_annotation(AnnotationState.NONE):
                # self.handleChildren(node)
                do_subscript()

        elif _is_name_or_attr(node.value, 'Annotated'):
            self.handleNode(node.value, node)

            # py39+
            if isinstance(node.slice, ast.Tuple):
                slice_tuple = node.slice
            # <py39
            elif (
                    isinstance(node.slice, ast.Index) and
                    isinstance(node.slice.value, ast.Tuple)
            ):
                slice_tuple = node.slice.value
            else:
                slice_tuple = None

            # not a multi-arg `Annotated`
            if slice_tuple is None or len(slice_tuple.elts) < 2:
                self.handleNode(node.slice, node)
            else:
                # the first argument is the type
                self.handleNode(slice_tuple.elts[0], node)
                # the rest of the arguments are not
                with self._enter_annotation(AnnotationState.NONE):
                    for arg in slice_tuple.elts[1:]:
                        self.handleNode(arg, node)

            self.handleNode(node.ctx, node)
        else:
            if _is_any_typing_member(node.value, self.scopeStack):
                with self._enter_annotation():
                    ### self.handleChildren(node)
                    do_subscript()
            else:
                ### self.handleChildren(node)
                do_subscript()

    #@+node:ekr.20240702085302.152: *4* Checker.TRY & TRYSTAR omit='body'
    def TRY(self, node):
        handler_names = []
        # List the exception handlers
        for i, handler in enumerate(node.handlers):
            if isinstance(handler.type, ast.Tuple):
                for exc_type in handler.type.elts:
                    handler_names.append(getNodeName(exc_type))
            elif handler.type:
                handler_names.append(getNodeName(handler.type))

            if handler.type is None and i < len(node.handlers) - 1:
                self.report(messages.DefaultExceptNotLast, handler)
        # Memorize the except handlers and process the body
        self.exceptHandlers.append(handler_names)
        for child in node.body:
            self.handleNode(child, node)
        self.exceptHandlers.pop()
        # Process the other nodes: "except:", "else:", "finally:"
        if 0:  ### Legacy. Works.
            self.handleChildren(node, omit='body')
        else:
            for field in ('handlers', 'orelse', 'finalbody'):
                statements = getattr(node, field, [])
                for statement in statements:
                    self.handleNode(statement, node)

    TRYSTAR = TRY

    #@+node:ekr.20240702085302.149: *4* Checker.TUPLE & LIST
    def TUPLE(self, node):
        if isinstance(node.ctx, ast.Store):
            # Python 3 advanced tuple unpacking: a, *b, c = d.
            # Only one starred expression is allowed, and no more than 1<<8
            # assignments are allowed before a stared expression. There is
            # also a limit of 1<<24 expressions after the starred expression,
            # which is impossible to test due to memory restrictions, but we
            # add it here anyway
            has_starred = False
            star_loc = -1
            for i, n in enumerate(node.elts):
                if isinstance(n, ast.Starred):
                    if has_starred:
                        self.report(messages.TwoStarredExpressions, node)
                        # The SyntaxError doesn't distinguish two from more
                        # than two.
                        break
                    has_starred = True
                    star_loc = i
            if star_loc >= 1 << 8 or len(node.elts) - star_loc - 1 >= 1 << 24:
                self.report(messages.TooManyExpressionsInStarredAssignment, node)
        self.handleChildren(node)

    LIST = TUPLE

    #@+node:ekr.20240702085302.159: *4* Checker.TYPEALIAS
    def TYPEALIAS(self, node):
        self.handleNode(node.name, node)
        with self._type_param_scope(node):
            self.handle_annotation_always_deferred(node.value, node)
    #@+node:ekr.20240702085302.158: *4* Checker.TYPEVAR, PARAMSPEC & TYPEVARTUPLE
    def TYPEVAR(self, node):
        self.handleNodeStore(node)
        self.handle_annotation_always_deferred(node.bound, node)

    PARAMSPEC = TYPEVARTUPLE = handleNodeStore

    #@+node:ekr.20240702085302.142: *4* Checker.YIELD
    def YIELD(self, node):
        if isinstance(self.scope, (ClassScope, ModuleScope)):
            self.report(messages.YieldOutsideFunction, node)
            return

        self.handleNode(node.value, node)

    AWAIT = YIELDFROM = YIELD

    #@-others
#@-others
#@@language python
#@@tabwidth -4
#@-leo
