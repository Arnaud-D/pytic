import os
import pathlib
import re
_package_path = pathlib.Path(os.path.dirname(__file__))


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
        self.filename_grammar = _package_path / "historic.lark"

    def parse(self):
        frames = self.parse_frames()
        times = self.parse_times()
        for (f, t) in zip(frames, times):
            f['timestamp'] = {'valid': True, 'data': t}
        return frames

    def parse_frames(self):
        with open(self.filename_data, "rb") as file_data:
            data = file_data.read().decode('ascii')
        pattern_frame = re.compile("\x02(?P<frame_content>.*?)(?P<terminator>[\x03\x04])", flags=re.DOTALL)
        pattern_group = re.compile("\n(?P<payload>.*?) (?P<checksum>.)\r", flags=re.DOTALL)
        pattern_payload = re.compile("(?P<label>[^ ]+?) (?P<data>.*)")
        match_frames = pattern_frame.finditer(data)
        frames = []
        for frame in match_frames:
            if frame.group('terminator') == "\x04":
                continue
            match_groups = pattern_group.finditer(frame.group('frame_content'))
            frame = {}
            for match_group in match_groups:
                payload = match_group.group('payload')
                expected_checksum = match_group.group('checksum')
                match_label_data = pattern_payload.match(payload)
                label = match_label_data.group('label')
                data = match_label_data.group('data')
                validity = checksum(payload) == expected_checksum
                frame[label] = {'valid': validity,
                                'data': data}
            frames.append(frame)
        return frames

    def parse_times(self):
        with open(self.filename_time, "r") as f:
            times = [int(l) for l in f.readlines()]
        return times


def checksum(checkfield):
    """Compute the checksum for a data group."""
    return chr((sum([ord(c) for c in checkfield]) & 0x3F) + 0x20)
