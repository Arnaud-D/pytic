import json
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
import tic_parser


def create(meter_mode, data_filename, time_filename):
    parser = tic_parser.create(meter_mode, data_filename, time_filename)
    frames = parser.parse()
    analyzer = Analyzer()
    analyzer.datastore = JsonHistoricDataStore(frames)
    analyzer.analyze()
    return analyzer


class Analyzer:
    @staticmethod
    def compute_avgpower(index_values, time):
        # Filter index values using Savitzky Golay filter. We pretend that the data points are equally spaced.
        # 195 samples <=> 5 min of data @ 1.55 frames/s
        dtime = [time[i+1] - time[i] for i in range(len(time)-1)]
        delta = sum(dtime) / len(dtime)
        deriv_index_values_f = savgol_filter(index_values, 195, 2, deriv=1, delta=delta)
        j_per_wh = 3.6e6  # joules per watt-hour
        deriv_index_values = [d * j_per_wh for d in deriv_index_values_f]
        avgpower_validity = [True] * len(deriv_index_values)
        return time, deriv_index_values, avgpower_validity

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

    def __init__(self, frames):
        self.frames = frames

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


class JsonHistoricAnalyzer(Analyzer):
    def __init__(self, filename):
        super().__init__()
        self.datastore = JsonHistoricDataStore(filename)
        self.analyze()

    def analyze(self):
        raise NotImplementedError
