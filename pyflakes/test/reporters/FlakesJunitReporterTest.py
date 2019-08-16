import os
import unittest

import xmlschema

from pyflakes.reporters.FlakesJunitReporter import FlakesJunitReporter
from pyflakes.reporters.pyflakesJsonLoader import pyflakesJsonLoader


def get_path(filename):
    file_path = os.path.join(os.path.dirname(__file__),
                             'test_files/',
                             filename)
    return file_path


class JunitReporterTest(unittest.TestCase):

    def test_empty(self):
        junit_schema = xmlschema.XMLSchema(get_path('junit.xsd'))
        with open(get_path('empty.json')) as test_file:
            loader = pyflakesJsonLoader()
            junit = FlakesJunitReporter(loader, test_file)
            self.assertTrue(junit_schema.is_valid(junit.to_output()))

    def test_syntax_error(self):
        junit_schema = xmlschema.XMLSchema(get_path('junit.xsd'))
        with open(get_path('syntax_error.json')) as test_file:
            loader = pyflakesJsonLoader()
            junit = FlakesJunitReporter(loader, test_file)
            self.assertTrue(junit_schema.is_valid(junit.to_output()))

    def test_section_cli(self):
        junit_schema = xmlschema.XMLSchema(get_path('junit.xsd'))
        with open(get_path('normal.json')) as test_file:
            loader = pyflakesJsonLoader()
            junit = FlakesJunitReporter(loader, test_file)
            self.assertTrue(junit_schema.is_valid(junit.to_output()))


if __name__ == '__main__':
    unittest.main()
