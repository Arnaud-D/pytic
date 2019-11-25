import json
import matplotlib.pyplot as plt


class Analyzer:
    @staticmethod
    def compute_avgpower(index_values, time):
        didx = 200  # around 5 min averaging @ 1.55 frames per second
        time_avgpower = time[:-didx]
        avgpower_validity = [True] * len(time_avgpower)
        d_time = [time[i + didx] - time[i] for i in range(len(time) - didx)]
        j_per_wh = 3.6e6  # joules per watt-hour
        avgpower_values = [(index_values[i + didx] - index_values[i]) * j_per_wh / d_time[i] for i in
                           range(len(d_time))]
        return time_avgpower, avgpower_values, avgpower_validity

    def __init__(self):
        self.power = None
        self.index = None
        self.avgpower = None
        self.datastore = None

    def analyze(self):
        time, _ = self.datastore.select('timestamp')
        power_values, power_validity = self.datastore.select('PAPP')
        index_values, index_validity = self.datastore.select('BASE')

        # Compute derived data
        time_avgpower, avgpower_values, avgpower_validity = self.compute_avgpower(index_values, time)

        self.power = TimeSeries(time, power_values, power_validity)
        self.index = TimeSeries(time, index_values, index_validity)
        self.avgpower = TimeSeries(time_avgpower, avgpower_values, avgpower_validity)

    def get_figure_power(self, width, height, dpi):
        figure = plt.Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        ax = figure.add_subplot(111)
        ax.plot(self.power.time, self.power.values)
        ax.set_xlabel("Temps (s)")
        ax.set_ylabel("Puissance apparente (VA)")
        invalid_data = [self.power.values[i] for i in range(len(self.power.validity)) if not self.power.validity[i]]
        invalid_time = [self.power.time[i] for i in range(len(self.power.validity)) if not self.power.validity[i]]
        figure.gca().plot(invalid_time, invalid_data, 'r. ')
        return figure

    def get_figure_index(self, width, height, dpi):
        figure = plt.Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        ax = figure.add_subplot(111)
        ax.plot(self.index.time, self.index.values)
        ax.set_xlabel("Temps (s)")
        ax.set_ylabel("Index (kWh)")
        invalid_data = [self.index.values[i] for i in range(len(self.index.validity)) if not self.index.validity[i]]
        invalid_time = [self.index.time[i] for i in range(len(self.index.validity)) if not self.index.validity[i]]
        figure.gca().plot(invalid_time, invalid_data, 'r. ')
        return figure

    def get_figure_avgpower(self, width, height, dpi):
        figure = plt.Figure(figsize=(width/dpi, height/dpi), dpi=dpi)
        ax = figure.add_subplot(111)
        ax.plot(self.avgpower.time, self.avgpower.values)
        ax.set_xlabel("Temps (s)")
        ax.set_ylabel("Puissance moyenne (W)")
        invalid_data = [self.avgpower.values[i] for i in range(len(self.avgpower.validity)) if not self.avgpower.validity[i]]
        invalid_time = [self.avgpower.time[i] for i in range(len(self.avgpower.validity)) if not self.avgpower.validity[i]]
        figure.gca().plot(invalid_time, invalid_data, 'r. ')
        return figure

    def get_figure_hist_power_time(self, width, height, dpi):
        figure = plt.Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        ax = figure.add_subplot(2, 1, 1)
        dtime = [self.avgpower.time[i+1] - self.avgpower.time[i] for i in range(len(self.avgpower.time)-1)]
        ax.hist(self.avgpower.values[:-1], bins=range(0, 6000, 200), weights=dtime)
        ax.set_xlabel("Puissance moyenne (W)")
        ax.set_ylabel("Durée (s)")

        ax = figure.add_subplot(2, 1, 2)
        ax.hist(self.avgpower.values[:-1], bins=range(0, 6000, 50), weights=dtime, cumulative=True, density=True)
        ax.grid()
        ax.set_ylabel("Durée cumulée normalisée")
        ax.set_xlabel("Puissance moyenne (W)")
        return figure

    def get_figure_hist_power_energy(self, width, height, dpi):
        figure = plt.Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        ax = figure.add_subplot(2, 1, 1)
        kwh_per_j = 1/3.6e6
        energy = [(self.avgpower.time[i+1] - self.avgpower.time[i])*self.avgpower.values[i]*kwh_per_j for i in range(len(self.avgpower.time)-1)]
        ax.hist(self.avgpower.values[:-1], bins=range(0, 6000, 50), weights=energy)
        ax.set_ylabel("Énergie (kWh)")

        ax = figure.add_subplot(2, 1, 2)
        ax.hist(self.avgpower.values[:-1], bins=range(0, 6000, 50), weights=energy, cumulative=True, density=True)
        ax.grid()
        ax.set_ylabel("Énergie cumulée normalisée")
        ax.set_xlabel("Puissance moyenne (W)")
        return figure


class TimeSeries:
    def __init__(self, time, values, validity):
        self.time = time
        self.values = values
        self.validity = validity


class JsonHistoricDataStore:
    @staticmethod
    def load(filename):
        """Load data from a file."""
        frames = []
        with open(filename, "r") as f:
            for line in f.readlines():
                frames.append(json.loads(line))
        return frames

    def __init__(self, filename):
        self.frames = self.load(filename)

    def select(self, field):
        if field == "timestamp":
            return self.select_timestamp()
        elif field == "PAPP":
            return self.select_papp()
        elif field == "BASE":
            return self.select_base()
        else:
            raise KeyError

    def select_timestamp(self):
        time = []
        validity = []
        s_per_ms = 0.001
        for frame in self.frames:
            time.append(frame['timestamp']['data'] * s_per_ms)
            validity.append(frame['timestamp']['valid'])
        return time, validity

    def select_papp(self):
        papp = []
        validity = []
        for frame in self.frames:
            try:
                if frame['PAPP']['valid']:
                    papp.append(int(frame['PAPP']['data']))
                else:
                    papp.append(papp[-1])
                validity.append(frame['PAPP']['valid'])
            except (ValueError, KeyError):
                if papp:
                    papp.append(papp[-1])
                papp.append(papp[-1])
                validity.append(False)
        return papp, validity

    def select_base(self):
        base = []
        validity = []
        kwh_per_wh = 0.001
        for frame in self.frames:
            try:
                if frame['BASE']['valid']:
                    base.append(int(frame['BASE']['data']) * kwh_per_wh)
                else:
                    base.append(base[-1])
                validity.append(frame['BASE']['valid'])
            except (ValueError, KeyError):
                if base:
                    base.append(base[-1])
                validity.append(False)
        return base, validity


class CsvHistoricDataStore:
    @staticmethod
    def load(filename):
        """Load data from a file."""
        frames = []
        with open(filename, "r") as f:
            for line in f.readlines():
                frames.append(line.split(','))
        return frames

    def __init__(self, filename):
        self.frames = self.load(filename)

    def select(self, field):
        """Extract a field from the data."""
        if field == "timestamp":
            return self.select_timestamp()
        elif field == "PAPP":
            return self.select_papp()
        elif field == "BASE":
            return self.select_base()
        else:
            raise KeyError

    def select_timestamp(self):
        timestamp = []
        s_per_ms = 0.001
        for frame in self.frames:
            timestamp.append(int(frame[0]) * s_per_ms)
        validity = [True] * len(self.frames)
        return timestamp, validity

    def select_papp(self):
        papp = []
        validity = []
        for frame in self.frames:
            try:
                papp.append(int(frame[2]))
                validity.append(True)
            except ValueError:
                if papp:
                    papp.append(papp[-1])
                validity.append(False)
        return papp, validity

    def select_base(self):
        base = []
        validity = []
        kwh_per_wh = 0.001
        for frame in self.frames:
            try:
                base.append(int(frame[1]) * kwh_per_wh)
                validity.append(True)
            except ValueError:
                if base:
                    base.append(base[-1])
                validity.append(False)
        return base, validity


class JsonHistoricAnalyzer(Analyzer):
    def __init__(self, filename):
        super().__init__()
        self.datastore = JsonHistoricDataStore(filename)


class CsvHistoricAnalyzer(Analyzer):
    def __init__(self, filename):
        super().__init__()
        self.datastore = CsvHistoricDataStore(filename)


class JsonStandardAnalyzer(Analyzer):
    def __init__(self, filename):
        super().__init__()

    def analyze(self):
        raise NotImplementedError


class CsvStandardAnalyzer(Analyzer):
    def __init__(self, filename):
        super().__init__()

    def analyze(self):
        raise NotImplementedError
