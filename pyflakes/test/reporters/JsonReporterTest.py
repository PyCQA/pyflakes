import os
import unittest

from pyflakes.reporters.JsonReporter import JsonReporter


def get_path(filename):
    file_path = os.path.join(os.path.dirname(__file__),
                             'test_files/',
                             filename)
    return file_path


class JsonReporterTest(unittest.TestCase):

    def test_empty(self):
        filename = 'no_errors.py'
        codeString = 'print("no errors in this file")'
        flakes_json = JsonReporter(codeString, filename).to_output()
        with open(get_path('empty.json')) as json_file:
            empty_json = json_file.read()
        self.assertEqual(flakes_json, empty_json)

    def test_syntax_error(self):
        filename = 'syntax_error.py'
        codeString = 'def'
        flakes_json = JsonReporter(codeString, filename).to_output()
        with open(get_path('syntax_error.json')) as json_file:
            syntax_error_json = json_file.read()
        self.assertEqual(flakes_json, syntax_error_json)

    def test_normal(self):
        filename = 'test_normal.py'
        codeString = 'import sys\nprint("one")\nimport datetime'
        flakes_json = JsonReporter(codeString, filename).to_output()
        with open(get_path('normal.json')) as json_file:
            normal_json = json_file.read()
        self.assertEqual(flakes_json, normal_json)


if __name__ == '__main__':
    unittest.main()
