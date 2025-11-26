#@+leo-ver=5-thin
#@+node:ekr.20251125174431.1: * @file plugins/leo_plugin.py
"""A plugin for pyflakes that improves testing of ast.ATTRIBUTE nodes."""

import ast
import os

#@+others
#@+node:ekr.20251126064813.1: ** leo_plugin: funcToMethod
def funcToMethod(f: Callable, theClass: object, name: str = None) -> None:
    """
    From the Python Cookbook...

    The following method allows you to add a function as a method of
    any class. That is, it converts the function to a method of the
    class. The method just added is available instantly to all
    existing instances of the class, and to all instances created in
    the future.

    The function's first argument should be self.

    The newly created method has the same name as the function unless
    the optional name argument is supplied, in which case that name is
    used as the method name.
    """
    setattr(theClass, name or f.__name__, f)

#@+node:ekr.20251126060205.1: ** leo_plugin: patched_ATTRIBUTE
def patched_ATTRIBUTE(self, node) -> None:
    if isinstance(node.ctx, ast.Load):
        if isinstance(node.value, ast.Name):
            if 1:  ### Don't put this in production code!
                print(f"patched_ATTRIBUTE: load {node.value.id}.{node.attr}")
    self.handleChildren(node)
#@+node:ekr.20251126054330.1: ** leo_plugin: register
def register(pyflakes) -> None:
    """Register the leo_plugin plugin."""
    if 0:
        path, extension = os.path.splitext(__file__)
        print(f"V6: {os.path.basename(path)}.register: pyflakes: {pyflakes!r}")

    # Patch pyflakes.ATTRIBUTE.
    funcToMethod(patched_ATTRIBUTE, pyflakes.__class__, 'ATTRIBUTE')
#@-others
#@-leo
