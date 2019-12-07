import matplotlib
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
import analyzer

matplotlib.use("TkAgg")


class FigurePane(ttk.Frame):
    """Widget displaying a figure in a pane."""
    def __init__(self, parent, width, height, name):
        super().__init__(parent, width=width, height=height)
        self.figure = plt.Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.name = name
        self.fig_fun = None

    def update_fig(self):
        width, height = self.canvas.get_width_height()
        dpi = 100
        self.canvas.figure = self.fig_fun(width, height, dpi)
        self.canvas.draw()


class ModeSelector(ttk.Frame):
    """Widget for mode selection."""
    def __init__(self, parent):
        super().__init__(parent)
        self.grid_columnconfigure(index=0, weight=1, minsize=100)
        self.grid_columnconfigure(index=1, weight=0, minsize=50)
        self.label = tk.Label(self, text="Mode du compteur")
        self.label.grid(column=0, row=0, sticky=tk.W)
        self.selected_mode = tk.StringVar(None, "historic")
        self.historic_mode = tk.Radiobutton(self, text="Historique", variable=self.selected_mode, value="historic",
                                            padx=20)
        self.historic_mode.grid(column=0, row=1, sticky=tk.W)
        self.standard_mode = tk.Radiobutton(self, text="Standard", variable=self.selected_mode, value="standard",
                                            padx=20)
        self.standard_mode.grid(column=0, row=2, sticky=tk.W)

    def get_mode(self):
        return self.selected_mode.get()


class FilenameSelector(ttk.Frame):
    """Widget for file selection."""
    @staticmethod
    def get_path(data_file_entry):
        """Action when clicking on the browse button."""
        file = fd.askopenfilename()
        if file != ():
            data_file_entry.delete(0, last=tk.END)
            data_file_entry.insert(0, file)

    def __init__(self, parent, text):
        super().__init__(parent)
        self.file_prompt = tk.Label(self, text=text)
        self.file_prompt.grid(column=0, row=0, sticky=tk.W)
        self.file_entry = tk.Entry(self, width=25)
        self.file_entry.grid(column=0, row=1, sticky=tk.W + tk.E)
        self.file_browse = tk.Button(self, text="...")
        self.file_browse.grid(column=1, row=1)
        self.file_browse["command"] = (lambda: self.get_path(self.file_entry))

    def get_filename(self):
        return self.file_entry.get()


class DataFilenameSelector(FilenameSelector):
    """Widget for the selection of the data file."""
    def __init__(self, parent):
        super().__init__(parent, "Fichier de données :")


class TimeFilenameSelector(FilenameSelector):
    """Widget for the selection of the time file."""
    def __init__(self, parent):
        super().__init__(parent, "Fichier de temps :")


class ImportButton(tk.Button):
    """Button to validate import."""
    def __init__(self, parent):
        super().__init__(parent, text="Importer")

    def set_action(self, import_action):
        self["command"] = import_action


class ConfigPane(ttk.Frame):
    """Pane regrouping configuration widgets."""
    def __init__(self, parent):
        super().__init__(parent, width=300, height=500)
        self.grid_columnconfigure(index=0, weight=1, minsize=100)


class DisplayArea(ttk.Notebook):
    """Widget for data display."""
    def __init__(self, parent):
        super().__init__(parent, width=800, height=500)
        w, h = 800, 500
        self.figure_panes = {'index': FigurePane(self, w, h, "Index"),
                             'power': FigurePane(self, w, h, "Puissance apparente"),
                             'avgpower': FigurePane(self, w, h, "Puissance moyenne"),
                             'histpowertime': FigurePane(self, w, h, "Durée vs puissance moyenne"),
                             'histpowerenergy': FigurePane(self, w, h, "Énergie vs puissance moyenne")}
        for fp in self.figure_panes.values():
            self.add(fp, text=fp.name)

    def set_figure_functions(self, functions):
        for (k, f) in functions.items():
            self.figure_panes[k].fig_fun = f

    def update_figures(self):
        for fp in self.figure_panes.values():
            fp.update_fig()


class MainWindow(tk.PanedWindow):
    def __init__(self, parent):
        super().__init__(parent, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)


class Gui:
    def __init__(self, title):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.config(padx=0)
        self.root.config(pady=0)

        self.main_window = MainWindow(self.root)

        self.config_pane = ConfigPane(self.main_window)
        self.mode_selector = ModeSelector(self.config_pane)
        self.datafilename_selector = DataFilenameSelector(self.config_pane)
        self.timefilename_selector = TimeFilenameSelector(self.config_pane)
        self.import_button = ImportButton(self.config_pane)

        self.display_area = DisplayArea(self.main_window)

        self.main_window.add(self.config_pane)
        self.main_window.add(self.display_area)
        self.main_window.pack(expand=True, fill='both')
        self.config_pane.grid(column=0, row=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.display_area.grid(column=1, row=0, sticky=tk.W+tk.E)
        self.datafilename_selector.grid(column=0, row=0, sticky=tk.W)
        self.timefilename_selector.grid(column=0, row=1, sticky=tk.W)
        self.mode_selector.grid(column=0, row=2, sticky=tk.W)
        self.import_button.grid(column=0, row=3, sticky=tk.W+tk.E)

    def get_meter_mode(self):
        return self.mode_selector.get_mode()

    def get_datafilename(self):
        return self.datafilename_selector.get_filename()

    def get_timefilename(self):
        return self.timefilename_selector.get_filename()

    def set_import_action(self, import_action):
        self.import_button.set_action(import_action)

    def set_figure_functions(self, functions):
        self.display_area.set_figure_functions(functions)

    def update_figures(self):
        self.display_area.update_figures()

    def mainloop(self):
        self.root.mainloop()


class Interface:
    def __init__(self, title):
        self.gui = Gui(title)
        self.gui.set_import_action(self.import_button_action)
        self.anl = None

    def import_button_action(self):
        meter_mode = self.gui.get_meter_mode()
        datafilename = self.gui.get_datafilename()
        timefilename = self.gui.get_timefilename()
        try:
            self.anl = analyzer.create(meter_mode, datafilename, timefilename)
        except FileNotFoundError:
            mb.showerror("Erreur", "L'import du fichier a échoué. Le fichier n'existe pas.")
            return
        except ValueError as e:
            print(e)
            mb.showerror("Erreur", "L'import du fichier a échoué. Le fichier est probablement corrompu.")
            return
        except NotImplementedError:
            mb.showinfo("Information", "L'import du fichier a échoué. La fonctionnalité n'est pas encore disponible.")
            return

        fig_funs = {'index': self.anl.get_figure_index,
                    'power': self.anl.get_figure_power,
                    'avgpower': self.anl.get_figure_avgpower,
                    'histpowertime': self.anl.get_figure_hist_power_time,
                    'histpowerenergy': self.anl.get_figure_hist_power_energy}
        self.gui.set_figure_functions(fig_funs)
        self.gui.update_figures()

    def mainloop(self):
        self.gui.mainloop()
