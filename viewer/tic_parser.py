import re


def create(meter_mode, filename_data, filename_time=None):
    if meter_mode == "historic":
        return HistoricParser(filename_data, filename_time)
    elif meter_mode == "standard":
        raise NotImplementedError
    else:
        raise ValueError(meter_mode)


class HistoricParser:
    def __init__(self, filename_data, filename_time):
        self.filename_data = filename_data
        self.filename_time = filename_time

    def parse(self):
        frames = self.parse_frames()
        times = self.parse_times()
        for (f, t) in zip(frames, times):
            f[b'timestamp'] = t
        return frames

    def parse_frames(self):
        with open(self.filename_data, "rb") as f:
            data = f.read()
        pattern_frame = re.compile(b"\x02(?P<frame_content>.*?)(?P<terminator>[\x03\x04])", flags=re.DOTALL)
        pattern_group = re.compile(b"\n(?P<payload>.*?) (?P<checksum>.)\r", flags=re.DOTALL)
        match_frames = pattern_frame.finditer(data)
        frames = []
        for m_frame in match_frames:
            frame_slice = data[slice(*m_frame.span('frame_content'))]
            if frame_slice[-1] == 0x04:  # skip truncated frames
                continue
            match_groups = pattern_group.finditer(frame_slice)
            frame = {b'ADCO': None, b'OPTARIF': None, b'ISOUSC': None, b'BASE': None, b'PTEC': None, b'IINST': None,
                     b'IMAX': None, b'PAPP': None, b'HHPHC': None, b'MOTDETAT': None}
            for match_group in match_groups:
                group = match_group.group(0)
                payload = group[1:-3]
                if checksum(payload) != group[-2]:
                    continue
                split = payload.split(b' ')
                label = split[0]
                if label not in frame.keys():
                    continue
                frame[label] = split[1]
            frames.append(frame)
        return frames

    def parse_times(self):
        with open(self.filename_time, "r") as f:
            times = [int(l) for l in f.readlines()]
        return times


def checksum(payload):
    """Compute the checksum for a data group."""
    return (sum(payload) & 0x3F) + 0x20
