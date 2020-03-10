import matplotlib.pyplot as plt
import scipy.signal
import numpy as np
import tic_parser

# Unit conversions
j_per_wh = 3.6e6  # J / Wh
s_per_ms = 0.001  # s / ms
kwh_per_wh = 0.001  # kWh / Wh
kwh_per_j = 1 / 3.6e6  # kWh / J
h_per_d = 24  # hours per day
s_per_h = 3600  # seconds per hour
d_per_w = 7  # days per week


def create(meter_mode, data_filename, time_filename=None):
    parser = tic_parser.create(meter_mode, data_filename, time_filename)
    frames = parser.parse()
    analyzer = Analyzer()
    analyzer.datastore = HistoricDatastore(frames)
    analyzer.analyze()
    return analyzer


class Analyzer:
    @staticmethod
    def compute_avgpower(index_values, time):
        # Compute power by using a derivating Savitzky Golay filter on the index.
        # We pretend that the data points are equally spaced.
        # 195 samples <=> 5 min of data @ 1.55 frames/s
        dt = np.average(np.diff(time))
        desired_window_length = 195
        index_length = len(index_values)
        window_length = desired_window_length if index_length > desired_window_length else index_length
        avgpower = scipy.signal.savgol_filter(index_values, window_length=window_length, polyorder=2, deriv=1, delta=dt)
        avgpower_validity = np.full_like(avgpower, True)
        return time, avgpower * j_per_wh, avgpower_validity

    @staticmethod
    def compute_seasonality(ts, period):
        nb_periods = int(np.floor(ts.time[-1]/period))
        if nb_periods < 1:
            raise ValueError(period)
        else:
            dt = np.average(np.diff(ts.time))  # average sample duration
            samples_per_period = int(np.floor(period / dt))
            nb_samples_to_select = nb_periods * samples_per_period
            time_trunc = ts.time[:nb_samples_to_select]
            values_trunc = ts.values[:nb_samples_to_select]
            period_average_filter = np.zeros(nb_samples_to_select + samples_per_period)
            mask = np.array(range(len(period_average_filter))) % samples_per_period == 0
            period_average_filter[mask] = 1/nb_periods
            period_average = np.convolve(values_trunc, period_average_filter)
            begin_index = len(values_trunc)
            end_index = len(period_average_filter)
            time_fin = time_trunc[0:samples_per_period]
            values_fin = period_average[begin_index:end_index]
            validity = np.full_like(time_fin, True)
            return TimeSeries(time_fin, values_fin, validity)

    def __init__(self):
        self.power = None
        self.index = None
        self.avgpower = None
        self.datastore = None

    def analyze(self):
        time, _ = self.datastore.get_field('timestamp')
        power_values, power_validity = self.datastore.get_field('PAPP')
        index_values, index_validity = self.datastore.get_field('BASE')

        # Compute derived data
        time_avgpower, avgpower_values, avgpower_validity = self.compute_avgpower(index_values, time)

        self.power = TimeSeries(time, power_values, power_validity)
        self.index = TimeSeries(time, index_values, index_validity)
        self.avgpower = TimeSeries(time_avgpower, avgpower_values, avgpower_validity)

    def get_figure_power(self, width, height, dpi):
        return Analyzer.get_figure_with_time(width, height, dpi, self.power, "Puissance apparente (VA)")

    def get_figure_index(self, width, height, dpi):
        return Analyzer.get_figure_with_time(width, height, dpi, self.index, "Index (kWh)")

    def get_figure_avgpower(self, width, height, dpi):
        return Analyzer.get_figure_with_time(width, height, dpi, self.avgpower, "Puissance moyenne (W)")

    def get_figure_day(self, width, height, dpi):
        try:
            average_day = Analyzer.compute_seasonality(self.avgpower, h_per_d * s_per_h)
            return Analyzer.get_figure_with_time(width, height, dpi, average_day, "Puissance moyenne (W)")
        except ValueError:
            return plt.Figure()

    def get_figure_week(self, width, height, dpi):
        try:
            average_day = Analyzer.compute_seasonality(self.avgpower, h_per_d * s_per_h * d_per_w)
            return Analyzer.get_figure_with_time(width, height, dpi, average_day, "Puissance moyenne (W)")
        except ValueError:
            return plt.Figure()

    @staticmethod
    def get_figure_with_time(width, height, dpi, timeseries, ylabel):
        figure = plt.Figure(figsize=(width/dpi, height/dpi), dpi=dpi)
        ax = figure.add_subplot(1, 1, 1)
        ax.plot(timeseries.time, timeseries.values)
        ax.set_xlabel("Temps (s)")
        ax.set_ylabel(ylabel)
        invalid_indices = np.logical_not(timeseries.validity)
        invalid_data = timeseries.values[invalid_indices]
        invalid_time = timeseries.time[invalid_indices]
        figure.gca().plot(invalid_time, invalid_data, 'r. ')
        return figure

    def get_figure_hist_power_time(self, width, height, dpi):
        figure = plt.Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        ax = figure.add_subplot(2, 1, 1)
        dt = np.diff(self.avgpower.time)
        ax.hist(self.avgpower.values[:-1], bins=range(0, 6000, 200), weights=dt)
        ax.set_ylabel("Durée (s)")

        ax = figure.add_subplot(2, 1, 2)
        ax.hist(self.avgpower.values[:-1], bins=range(0, 6000, 50), weights=dt, cumulative=True, density=True)
        ax.grid()
        ax.set_ylabel("Durée cumulée normalisée")
        ax.set_xlabel("Puissance moyenne (W)")
        return figure

    def get_figure_hist_power_energy(self, width, height, dpi):
        figure = plt.Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        ax = figure.add_subplot(2, 1, 1)
        energy = np.diff(self.avgpower.time) * self.avgpower.values[:-1] * kwh_per_j
        ax.hist(self.avgpower.values[:-1], bins=range(0, 6000, 50), weights=energy)
        ax.set_ylabel("Énergie (kWh)")

        ax = figure.add_subplot(2, 1, 2)
        ax.hist(self.avgpower.values[:-1], bins=range(0, 6000, 50), weights=energy, cumulative=True, density=True)
        ax.grid()
        ax.set_ylabel("Énergie cumulée normalisée")
        ax.set_xlabel("Puissance moyenne (W)")
        return figure


class TimeSeries:
    def __init__(self, time, values, validity=None):
        self.time = time
        self.values = values
        self.validity = validity


class HistoricDatastore:
    def __init__(self, frames):
        self.frames = frames
        self.length = len(self.frames)
        self.timestamp = self.extract('timestamp', s_per_ms, float)
        self.papp = self.extract('PAPP', 1, float)
        self.base = self.extract('BASE', kwh_per_wh, float)

    def get_field(self, field):
        if field == "timestamp":
            return self.timestamp
        elif field == "PAPP":
            return self.papp
        elif field == "BASE":
            return self.base
        else:
            raise ValueError(field)

    def extract(self, field, scaling, converter):
        data = np.zeros(self.length)
        validity = np.full(self.length, False)
        for k, frame in zip(range(self.length), self.frames):
            try:
                validity[k] = frame[field]['valid']
                data[k] = converter(frame[field]['data']) if validity[k] else data[k-1]
            except (ValueError, KeyError):  # Field does not exist or cannot be converted
                data[k] = data[k-1]
                # validity[k] already false by default
        return data * scaling, validity
