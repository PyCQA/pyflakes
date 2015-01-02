from pyflakes import messages as m
from pyflakes.test.harness import TestCase

class Test(TestCase):
    def test_Asserts_intentionally_simple_pass(self):
        self.flakes("""
        assert True
        assert False
        """)

    def test_Asserts_nontrivial_pass(self):
        self.flakes("""
        d = {'a': 1, 'b': 2}
        l = [1, 2]
        n = 10
        s = {1, 2}
        t = (1, 2)
        needle = 'needle'
        assert d == {'a': 3}
        assert n == 10
        assert l == [1, 2]        
        assert s == {1, 2}
        assert t == (1, 2)
        assert needle in "haystack"
        """)

    def test_Asserts_triviallyTrue_fail(self):
        self.flakes("""
        assert ("Any", "Tuple", "Really")
        assert "Non empty string"
        assert b"Non empty binary"
        assert ["Non", "empty", "list"]
        assert {1, 2, 3}
        assert {'a': 2, 'b': 3}
        assert 1
        assert 1.0
        """,
                    *[m.AssertTrivallyTrue]*8)

