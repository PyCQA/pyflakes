import re

from coala_json.loader.JsonLoader import JsonLoader


class pyflakesJsonLoader(JsonLoader):
    """
    Contains method to extract data from pyflakes-json
    """

    @staticmethod
    def sanitize(error_message):
        """
        Change HTML characters to character entity reference so that
        they are not mixed with XML tags

        :param: string that contains HTML characters
        :return: string with character entity references
        """
        mapping = {'\"': '&quot;', '<': '&lt;', '>': '&gt;'}
        for k, v in mapping.items():
            error_message = error_message.replace(k, v)
        return error_message

    @staticmethod
    def extract_error_code(error_message):
        return ''

    @staticmethod
    def extract_message(problem):
        return pyflakesJsonLoader.sanitize(problem['message'])

    @staticmethod
    def extract_raw_message(problem):
        return problem['message']

    @staticmethod
    def extract_affected_line(problem):
        return problem['line']

    @staticmethod
    def extract_affected_column(problem):
        return problem['column']

    @staticmethod
    def extract_file(problem):
        return problem['file']

    @staticmethod
    def extract_origin(problem):
        return 'pyflakes'

    @staticmethod
    def extract_severity(problem):
        return problem['severity'] if problem['severity'] else 1

    @staticmethod
    def extract_errors(problems):
        return len(problems)
