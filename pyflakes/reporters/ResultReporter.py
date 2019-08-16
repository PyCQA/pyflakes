from pyflakes.reporters.pyflakesJsonLoader import pyflakesJsonLoader


class ResultReporter:
    """
    Every test report class is a sub class of ResultReporter
    """

    def __init__(self, loader: pyflakesJsonLoader, flakes_json):
        self.loader = loader
        self.flakes_json = flakes_json
