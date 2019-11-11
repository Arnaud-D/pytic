import json


class Analyzer:
    def analyze(self):
        raise NotImplementedError


class JsonHistoricAnalyzer(Analyzer):
    def __init__(self, filename):
        self.filename = filename
        self.frames = []
        self.validity = []
        self.time = []
        self.power = []

    def analyze(self):
        self.load()
        power_str, self.validity = self.select('PAPP')
        self.time, _ = self.select('timestamp')
        self.power = list(map(int, power_str))

    def load(self):
        """Load data."""
        self.frames = []
        with open(self.filename) as f:
            for line in f.readlines():
                self.frames.append(json.loads(line))

    def select(self, field):
        """Extract a field from the data."""
        data = []
        validity = []
        for frame in self.frames:
            data.append(frame[field]['data'])
            validity.append(frame[field]['valid'])
        return data, validity


class CsvHistoricAnalyzer(Analyzer):
    def __init__(self, filename):
        self.filename = filename
        self.frames = []
        self.validity = []
        self.time = []
        self.power = []

    def analyze(self):
        try:
            self.load()
        except FileNotFoundError as e:
            raise e
        try:
            power_str, self.validity = self.select('PAPP')
            self.time, _ = self.select('timestamp')
            self.power = list(map(int, power_str))
        except Exception:
            raise ValueError

    def load(self):
        """Load data."""
        self.frames = []
        with open(self.filename) as f:
            for line in f.readlines():
                self.frames.append(line.split(','))

    def select(self, field):
        """Extract a field from the data."""
        data = []
        if field == "timestamp":
            index = 0
        elif field == "BASE":
            index = 1
        elif field == "PAPP":
            index = 2
        else:
            raise ValueError
        for frame in self.frames:
            data.append(int(frame[index]))
        validity = [True for _ in range(len(self.frames))]
        return data, validity


class JsonStandardAnalyzer(Analyzer):
    def __init__(self, filename):
        self.filename = filename

    def analyze(self):
        raise NotImplementedError


class CsvStandardAnalyzer(Analyzer):
    def __init__(self, filename):
        self.filename = filename

    def analyze(self):
        raise NotImplementedError
