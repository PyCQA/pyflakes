import textwrap, compiler
from twisted.trial import unittest

import pyflakes

class Test(unittest.TestCase):

    def run(self, input, *expectedOutputs):
        w = pyflakes.Checker(compiler.parse(textwrap.dedent(input)))
        outputs = [type(o) for o in w.messages]
        expectedOutputs = list(expectedOutputs)
        outputs.sort()
        expectedOutputs.sort()
        self.assert_(outputs == expectedOutputs, '''\
for input:
%s
expected outputs:
%s
but got:
%s''' % (input, repr(expectedOutputs), '\n'.join([str(o) for o in w.messages])))
