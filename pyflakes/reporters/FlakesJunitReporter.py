from coala_json.reporters.JunitReporter import JunitReporter

from pyflakes.reporters.ResultReporter import ResultReporter


class FlakesJunitReporter(ResultReporter):
    """
    Contain methods to produce Junit test report from flakes-json
    """

    def to_output(self):
        """
        Convert flakes-json output to flakes-junit test result report

        :return: junit test result report
        """
        junit = JunitReporter(self.loader, self.flakes_json)
        return junit.to_output()
