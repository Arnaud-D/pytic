import lark
import os
import pathlib
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
        with open(self.filename_grammar, "r") as file_grammar:
            parser = lark.Lark(file_grammar, parser="lalr", transformer=AstTransformer())
        frames = parser.parse(data)
        return frames

    def parse_times(self):
        with open(self.filename_time, "r") as f:
            times = [int(l) for l in f.readlines()]
        return times


def checksum(checkfield):
    """Compute the checksum for a data group."""
    return chr((sum([ord(c) for c in checkfield]) & 0x3F) + 0x20)


class AstTransformer(lark.Transformer):
    def group(self, args):
        payload_node = args[0]
        expected_checksum = args[1]
        checkfield = ''.join(payload_node.children)
        validity = expected_checksum == checksum(checkfield)
        return {'label': str(payload_node.children[0]),
                'data': str(payload_node.children[2]),
                'validity': validity}

    def complete_frame(self, args):
        dico = {}
        for c in args:
            dico[c['label']] = {}
            dico[c['label']]['valid'] = c['validity']
            dico[c['label']]['data'] = c['data']
        return dico

    def truncated_frame(self, args):
        return {}

    def start(self, args):
        frames = []
        for f in args:
            frames.append(f)
        return frames
