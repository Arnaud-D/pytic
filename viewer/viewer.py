import matplotlib
import matplotlib.pyplot as plt
import json
import tkinter as tk
from tkinter import ttk
import tkinter.filedialog as fd
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)

matplotlib.use("TkAgg")

WINDOW_TITLE = "Visionneuse Linkycom"
WINDOW_PADX = 0
WINDOW_PADY = 0

tick = "✓"


def load_data(filename):
    """Load data from a file."""
    frames = []
    with open(filename) as f:
        for line in f.readlines():
            frames.append(json.loads(line))
    return frames


def print_data(frames):
    for frame in frames:
        print("--- Start frame ---")
        for k in frame:
            print("{} {label:12}{value}".format("✓", label=k, value=frame[k]['data']))

        print("--- End frame ---")


def extract_data(label, frames):
    """Extract the data corresponding to a label from a dataset."""
    data = []
    for frame in frames:
        data.append(frame[label]['data'])
    return data


def get_path(data_file_entry):
    """Action when clicking on the browse button."""
    file = fd.askopenfilename()
    if file != ():
        data_file_entry.delete(0, last=tk.END)
        data_file_entry.insert(0, file)


figure = plt.Figure(figsize=(5, 4), dpi=100)


def import_file(data_file_entry, canvas):
    """Action when clicking on the import button."""
    global figure
    filename = data_file_entry.get()
    data = load_data(filename)
    power_raw = extract_data('PAPP', data)
    power = list(map(int, power_raw))
    figure = plt.Figure(figsize=(5, 4), dpi=100)
    figure.add_subplot(111).plot(power)
    print(len(power))

    canvas.figure = figure
    canvas.draw()


def main():
    """Main entry point."""

    # Root
    root = tk.Tk()
    root.title(WINDOW_TITLE)
    root.config(padx=WINDOW_PADX)
    root.config(pady=WINDOW_PADY)

    # Notebook and tabs
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=1)
    config = ttk.Frame()
    view = ttk.Frame()
    notebook.add(config, text="Configuration")
    notebook.add(view, text="Vue")

    # Config tab
    # -- Data file entry
    data_file_prompt = tk.Label(config, text="Fichier de données :")
    data_file_prompt.grid(column=0, row=0, sticky=tk.W)
    data_file_entry = tk.Entry(config, width=50)
    data_file_entry.grid(column=1, row=0)
    data_file_browse_button = tk.Button(config, text="...")
    data_file_browse_button.grid(column=2, row=0)
    # -- Import data button
    import_button = tk.Button(config, text="Importer")
    import_button.grid(column=3, row=0, columnspan=2, padx=(10, 0))

    # View tab
    canvas = FigureCanvasTkAgg(figure, master=view)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    toolbar = NavigationToolbar2Tk(canvas, root)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # Actions
    def data_file_browse_button_action():
        return get_path(data_file_entry)

    def import_button_action():
        return import_file(data_file_entry, canvas)

    data_file_browse_button["command"] = data_file_browse_button_action
    import_button["command"] = import_button_action

    root.mainloop()


if __name__ == "__main__":
    main()
