# (c) 2005 Divmod, Inc.  See LICENSE file for details

class Message(object):
    message = ''
    message_args = ()
    def __init__(self, filename, lineno):
        self.filename = filename
        self.lineno = lineno
    def __str__(self):
        return '%s:%s: %s' % (self.filename, self.lineno, self.message % self.message_args)


class UnusedImport(Message):
    message = '%r imported but unused'
    def __init__(self, filename, lineno, name):
        Message.__init__(self, filename, lineno)
        self.message_args = (name,)


class RedefinedWhileUnused(Message):
    message = 'redefinition of unused %r from line %r'
    def __init__(self, filename, lineno, name, orig_lineno):
        Message.__init__(self, filename, lineno)
        self.message_args = (name, orig_lineno)


class ImportStarUsed(Message):
    message = "'from %s import *' used; unable to detect undefined names"
    def __init__(self, filename, lineno, modname):
        Message.__init__(self, filename, lineno)
        self.message_args = (modname,)


class UndefinedName(Message):
    message = 'undefined name %r'
    def __init__(self, filename, lineno, name):
        Message.__init__(self, filename, lineno)
        self.message_args = (name,)


class DuplicateArgument(Message):
    message = 'duplicate argument %r in function definition'
    def __init__(self, filename, lineno, name):
        Message.__init__(self, filename, lineno)
        self.message_args = (name,)


class RedefinedFunction(Message):
    message = 'redefinition of fuction %r from line %r'
    def __init__(self, filename, lineno, name, orig_lineno):
        Message.__init__(self, filename, lineno)
        self.message_args = (name, orig_lineno)
