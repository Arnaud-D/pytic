import json


class Analyzer:
    def analyze(self):
        raise NotImplementedError


class JsonHistoricAnalyzer(Analyzer):
    def __init__(self, filename):
        self.filename = filename
        self.frames = []
        self.time = []
        self.power = []
        self.power_validity = []
        self.index = []
        self.index_validity = []
        self.avgpower = []
        self.time_avgpower = []
        self.avgpower_validity = []

    def analyze(self):
        self.load()
        power_str, self.power_validity = self.select('PAPP')
        self.time, _ = self.select('timestamp')
        self.power = list(map(int, power_str))
        index_str, self.index_validity = self.select('BASE')
        self.index = list(map(int, index_str))

        # Compute average power
        didx = 200  # around 5 min averaging @ 1.55 frames per second
        d_time = [self.time[i + didx] / 1000 - self.time[i] / 1000 for i in range(len(self.time) - didx)]
        j_per_wh = 3600  # joules per watt-hour
        self.avgpower = [(self.index[i + didx] - self.index[i]) * j_per_wh / d_time[i] for i in range(len(d_time))]
        self.time_avgpower = self.time[:-didx]
        self.avgpower_validity = [True for _ in range(len(self.time_avgpower))]

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
        self.time = []
        self.power = []
        self.power_validity = []
        self.index = []
        self.index_validity = []
        self.avgpower = []
        self.time_avgpower = []
        self.avgpower_validity = []

    def analyze(self):
        try:
            self.load()
        except FileNotFoundError as e:
            raise e
        try:
            self.time, _ = self.select('timestamp')
            power_str, self.power_validity = self.select('PAPP')
            self.power = list(map(int, power_str))
            index_str, self.index_validity = self.select('BASE')
            self.index = list(map(int, index_str))
        except Exception:
            raise ValueError
        # Compute average power
        didx = 200  # around 5 min averaging @ 1.55 frames per second
        d_time = [self.time[i + didx] / 1000 - self.time[i] / 1000 for i in range(len(self.time) - didx)]
        j_per_wh = 3600  # joules per watt-hour
        self.avgpower = [(self.index[i + didx] - self.index[i]) * j_per_wh / d_time[i] for i in range(len(d_time))]
        self.time_avgpower = self.time[:-didx]
        self.avgpower_validity = [True for _ in range(len(self.time_avgpower))]

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
