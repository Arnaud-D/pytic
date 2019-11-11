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

WINDOW_TITLE = "Visionneuse Linkycom"
WINDOW_PADX = 0
WINDOW_PADY = 0


def get_path(data_file_entry):
    """Action when clicking on the browse button."""
    file = fd.askopenfilename()
    if file != ():
        data_file_entry.delete(0, last=tk.END)
        data_file_entry.insert(0, file)


def update_figure(anl, canvas):
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


def main():
    """Main entry point."""

    # Root
    root = tk.Tk()
    root.title(WINDOW_TITLE)
    root.config(padx=WINDOW_PADX)
    root.config(pady=WINDOW_PADY)

    # Window
    window = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
    window.pack(expand=True, fill='both')
    # Panes
    config = ttk.Frame(window, width=300, height=500)
    config.grid(column=0, row=0, sticky=tk.W+tk.E)
    view = ttk.Frame(window, width=800, height=500)
    view.grid(column=1, row=0, sticky=tk.W+tk.E)
    window.add(config)
    config.grid_columnconfigure(index=0, weight=1, minsize=100)
    config.grid_columnconfigure(index=1, weight=0, minsize=50)
    window.add(view)

    # Config tab
    # - Data file
    # -- Data file label
    file_prompt = tk.Label(config, text="Fichier de données :")
    file_prompt.grid(column=0, row=0, sticky=tk.W)
    # -- Data file entry
    file_entry = tk.Entry(config, width=25)
    file_entry.grid(column=0, row=1, sticky=tk.W+tk.E)
    # -- Data file browse button
    file_browse = tk.Button(config, text="...")
    file_browse.grid(column=1, row=1)
    # -- Data file import button
    file_import = tk.Button(config, text="Importer")
    file_import.grid(column=0, row=8, columnspan=2, sticky=tk.W+tk.E)
    # - Mode selection
    # -- Mode label
    mode_label = tk.Label(config, text="Mode du compteur")
    mode_label.grid(column=0, row=2, sticky=tk.W)
    # -- Options
    selected_mode = tk.StringVar(None, "historic")
    historic_mode = tk.Radiobutton(config, text="Historique", variable=selected_mode, value="historic", padx=20)
    historic_mode.grid(column=0, row=3, sticky=tk.W)
    standard_mode = tk.Radiobutton(config, text="Standard", variable=selected_mode, value="standard", padx=20)
    standard_mode.grid(column=0, row=4, sticky=tk.W)
    # - Format selection
    # -- Mode label
    format_label = tk.Label(config, text="Format du fichier")
    format_label.grid(column=0, row=5, sticky=tk.W)
    selected_format = tk.StringVar(None, "csv")
    csv_format = tk.Radiobutton(config, text="CSV", variable=selected_format, value="csv", padx=20)
    csv_format.grid(column=0, row=6, sticky=tk.W)
    json_format = tk.Radiobutton(config, text="JSON", variable=selected_format, value="json", padx=20)
    json_format.grid(column=0, row=7, sticky=tk.W)

    # View tab
    figure = plt.Figure(figsize=(5, 4), dpi=100)
    canvas = FigureCanvasTkAgg(figure, master=view)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    toolbar = NavigationToolbar2Tk(canvas, view)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # Actions
    def data_file_browse_button_action():
        return get_path(file_entry)

    def import_button_action():
        mode = selected_mode.get()
        fmt = selected_format.get()
        filename = file_entry.get()
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
        update_figure(anl, canvas)

    file_browse["command"] = data_file_browse_button_action
    file_import["command"] = import_button_action

    root.mainloop()


if __name__ == "__main__":
    main()
