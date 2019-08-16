import ast
import json
import sys

from pyflakes import checker


class JsonReporter:
    """
    Contain methods to produce json report
    """

    def __init__(self, codeString, filename):
        self.codeString = codeString
        self.filename = filename

    def to_output(self):
        """
        Produce json output

        :return: json result report
        """
        results = []
        cli = {'cli': results}
        warning_dict = {}
        try:
            tree = ast.parse(self.codeString, filename=self.filename)
            file_tokens = checker.make_tokens(self.codeString)
            w = checker.Checker(tree, file_tokens=file_tokens,
                                filename=self.filename)
            w.messages.sort(key=lambda m: m.lineno)
            for warning in w.messages:
                warning_dict['message'] = str(warning).split(' ', 1)[1]
                warning = str(warning).split(' ', 1)[0]
                loc = str(warning).split(':')
                warning_dict['file'] = loc[0] if loc[0] else None
                warning_dict['line'] = loc[1] if loc[1] else None
                warning_dict['column'] = loc[2] if loc[2] else None
                results.append(warning_dict.copy())
        except SyntaxError:
            value = sys.exc_info()[1]
            msg = value.args[0]
            warning_dict['message'] = msg
            warning_dict['file'] = self.filename
            warning_dict['line'] = value.lineno if value.lineno else None
            warning_dict['column'] = value.offset if value.offset else None
            results.append(warning_dict.copy())

        flakes_json = {'results': cli}
        flakes_json = json.dumps(flakes_json, sort_keys=True, indent=2,
                                 separators=(',', ': '))
        return flakes_json + '\n'
