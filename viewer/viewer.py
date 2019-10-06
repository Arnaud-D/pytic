import matplotlib.pyplot as plt
import json

tick = "✓"


def load_data(filename):
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
    data = []
    for frame in frames:
        data.append(frame[label]['data'])
    return data


def main():
    print("Linkom Viewer 0.1")
    frames = load_data("data.json")
    print_data(frames)
    power_raw = extract_data('PAPP', frames)
    power = list(map(int, power_raw))

    plt.plot(power)
    plt.show()


if __name__ == "__main__":
    main()
