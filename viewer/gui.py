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


class Interface:
    def __init__(self, title):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.config(padx=0)
        self.root.config(pady=0)

        self.window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        self.window.pack(expand=True, fill='both')

        self.config_pane = ttk.Frame(self.window, width=300, height=500)
        self.config_pane.grid(column=0, row=0, sticky=tk.W + tk.E)
        self.view_pane = ttk.Frame(self.window, width=800, height=500)
        self.view_pane.grid(column=1, row=0, sticky=tk.W + tk.E)
        self.window.add(self.config_pane)
        self.config_pane.grid_columnconfigure(index=0, weight=1, minsize=100)
        self.config_pane.grid_columnconfigure(index=1, weight=0, minsize=50)
        self.window.add(self.view_pane)

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
        self.historic_mode = tk.Radiobutton(self.config_pane, text="Historique", variable=self.selected_mode, value="historic", padx=20)
        self.historic_mode.grid(column=0, row=3, sticky=tk.W)
        self.standard_mode = tk.Radiobutton(self.config_pane, text="Standard", variable=self.selected_mode, value="standard", padx=20)
        self.standard_mode.grid(column=0, row=4, sticky=tk.W)
        # - Format selection
        # -- Mode label
        self.format_label = tk.Label(self.config_pane, text="Format du fichier")
        self.format_label.grid(column=0, row=5, sticky=tk.W)
        self.selected_format = tk.StringVar(None, "csv")
        self.csv_format = tk.Radiobutton(self.config_pane, text="CSV", variable=self.selected_format, value="csv", padx=20)
        self.csv_format.grid(column=0, row=6, sticky=tk.W)
        self.json_format = tk.Radiobutton(self.config_pane, text="JSON", variable=self.selected_format, value="json", padx=20)
        self.json_format.grid(column=0, row=7, sticky=tk.W)

        # View tab
        self.figure = plt.Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.view_pane)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.view_pane)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.file_browse["command"] = (lambda: self.get_path(self.file_entry))
        self.file_import["command"] = self.import_button_action

    def import_button_action(self):
        mode = self.selected_mode.get()
        fmt = self.selected_format.get()
        filename = self.file_entry.get()
        if mode == "historic" and fmt == "json":
            anl = analyzer.JsonHistoricAnalyzer(filename)
        elif mode == "historic" and fmt == "csv":
            anl = analyzer.CsvHistoricAnalyzer(filename)
        elif mode == "standard" and fmt == "json":
            anl = analyzer.JsonStandardAnalyzer(filename)
        elif mode == "standard" and fmt == "csv":
            anl = analyzer.CsvStandardAnalyzer(filename)
        else:
            raise ValueError

        try:
            anl.analyze()
        except FileNotFoundError:
            mb.showerror("Erreur", "Erreur ! Le fichier '{}' n'existe pas.".format(filename))
            return
        except ValueError:
            mb.showerror("Erreur", "Erreur ! L'analyse du fichier a échoué.")
            return
        except NotImplementedError:
            mb.showinfo("Information", "La fonctionnalité n'est pas encore disponible.".format(filename))
            return
        self.update_figure(anl, self.canvas)

    def get_path(self, data_file_entry):
        """Action when clicking on the browse button."""
        file = fd.askopenfilename()
        if file != ():
            data_file_entry.delete(0, last=tk.END)
            data_file_entry.insert(0, file)

    def update_figure(self, anl, canvas):
        # Get data
        validity = anl.validity
        power = anl.power
        time = anl.time
        time_offset = [t/1000 - time[0]/1000 for t in time]
        # Plot
        width, height = canvas.get_width_height()
        dpi = 100
        figure = plt.Figure(figsize=(width/dpi, height/dpi), dpi=dpi)
        figure.add_subplot(111).plot(time_offset, power)
        validity_markers_invalid = [power[i] for i in range(len(validity)) if not validity[i]]
        time_markers_invalid = [time_offset[i] for i in range(len(validity)) if not validity[i]]
        figure.gca().plot(time_markers_invalid, validity_markers_invalid, 'r. ')

        canvas.figure = figure
        canvas.draw()

    def mainloop(self):
        self.root.mainloop()
