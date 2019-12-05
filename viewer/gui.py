import matplotlib
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
import analyzer
import json

matplotlib.use("TkAgg")


class FigurePane(ttk.Frame):
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


class Interface:
    @staticmethod
    def get_path(data_file_entry):
        """Action when clicking on the browse button."""
        file = fd.askopenfilename()
        if file != ():
            data_file_entry.delete(0, last=tk.END)
            data_file_entry.insert(0, file)

    def __init__(self, title):
        self.anl = None
        self.root = tk.Tk()
        self.root.title(title)
        self.root.config(padx=0)
        self.root.config(pady=0)

        self.window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        self.window.pack(expand=True, fill='both')

        self.config_pane = ttk.Frame(self.window, width=300, height=500)
        self.config_pane.grid(column=0, row=0, sticky=tk.W + tk.E)
        self.config_pane.grid_columnconfigure(index=0, weight=1, minsize=100)
        self.config_pane.grid_columnconfigure(index=1, weight=0, minsize=50)
        self.window.add(self.config_pane)

        self.notebook = ttk.Notebook(self.window, width=800, height=500)
        self.notebook.grid(column=1, row=0, sticky=tk.W + tk.E)

        w, h = 800, 500
        self.figure_panes = {'index': FigurePane(self.notebook, w, h, "Index"),
                             'power': FigurePane(self.notebook, w, h, "Puissance apparente"),
                             'avgpower': FigurePane(self.notebook, w, h, "Puissance moyenne"),
                             'histpowertime': FigurePane(self.notebook, w, h, "Durée vs puissance moyenne"),
                             'histpowerenergy': FigurePane(self.notebook, w, h, "Énergie vs puissance moyenne")}
        for fp in self.figure_panes.values():
            self.notebook.add(fp, text=fp.name)
        self.window.add(self.notebook)

        self.file_prompt = tk.Label(self.config_pane, text="Fichier de données :")
        self.file_prompt.grid(column=0, row=0, sticky=tk.W)
        # -- Data file entry
        self.file_entry = tk.Entry(self.config_pane, width=25)
        self.file_entry.grid(column=0, row=1, sticky=tk.W + tk.E)
        # -- Data file browse button
        self.file_browse = tk.Button(self.config_pane, text="...")
        self.file_browse.grid(column=1, row=1)
        # -- Data file import button
        self.file_import = tk.Button(self.config_pane, text="Importer")
        self.file_import.grid(column=0, row=8, columnspan=2, sticky=tk.W + tk.E)
        # - Mode selection
        # -- Mode label
        self.mode_label = tk.Label(self.config_pane, text="Mode du compteur")
        self.mode_label.grid(column=0, row=2, sticky=tk.W)
        # -- Options
        self.selected_mode = tk.StringVar(None, "historic")
        self.historic_mode = tk.Radiobutton(self.config_pane, text="Historique", variable=self.selected_mode,
                                            value="historic", padx=20)
        self.historic_mode.grid(column=0, row=3, sticky=tk.W)
        self.standard_mode = tk.Radiobutton(self.config_pane, text="Standard", variable=self.selected_mode,
                                            value="standard", padx=20)
        self.standard_mode.grid(column=0, row=4, sticky=tk.W)
        # - Format selection
        # -- Mode label
        self.format_label = tk.Label(self.config_pane, text="Format du fichier")
        self.format_label.grid(column=0, row=5, sticky=tk.W)
        self.selected_format = tk.StringVar(None, "json")
        self.csv_format = tk.Radiobutton(self.config_pane, text="CSV", variable=self.selected_format, value="csv",
                                         padx=20)
        self.csv_format.grid(column=0, row=6, sticky=tk.W)
        self.json_format = tk.Radiobutton(self.config_pane, text="JSON", variable=self.selected_format, value="json",
                                          padx=20)
        self.json_format.grid(column=0, row=7, sticky=tk.W)

        self.file_browse["command"] = (lambda: self.get_path(self.file_entry))
        self.file_import["command"] = self.import_button_action

    def import_button_action(self):
        mode = self.selected_mode.get()
        fmt = self.selected_format.get()
        filename = self.file_entry.get()
        try:
            self.anl = analyzer.create(mode, fmt, filename)
        except FileNotFoundError:
            mb.showerror("Erreur", "L'import du fichier a échoué. Le fichier n'existe pas.")
            return
        except json.JSONDecodeError:
            mb.showerror("Erreur", "L'import du fichier a échoué. Le fichier n'est pas un fichier JSON valide.")
            return
        except ValueError:
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
        for k, fp in self.figure_panes.items():
            fp.fig_fun = fig_funs[k]
            fp.update_fig()

    def mainloop(self):
        self.root.mainloop()
