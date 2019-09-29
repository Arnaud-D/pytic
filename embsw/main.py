import pyb
import ujson

cfg = dict()
cfg['historic'] = {'baudrate': 1200,
                   'bits': 7,
                   'parity': 0,
                   'stop': 1,
                   }
cfg['standard'] = {'baudrate': 9600,
                   'bits': 7,
                   'parity': 0,
                   'stop': 1,
                   }
sym = {'STX': 0x02,
       'ETX': 0x03,
       'LF': 0x0A,
       'CR': 0x0D,
       'EOT': 0x04,
       'SP': 0x20,
       }


class StreamParser:
    """Parse a stream into frames."""
    # Receiver states
    PARSER_WAITING = 0
    PARSER_RECEIVING = 1
    # Frame status
    FRAME_COMPLETE = 0
    FRAME_TRUNCATED = 1
    FRAME_UNAVAILABLE = 2

    def __init__(self):
        self.state = StreamParser.PARSER_WAITING
        self.old_state = StreamParser.PARSER_WAITING
        self.frame = []
        self.status = StreamParser.FRAME_UNAVAILABLE

    def set_state(self, state):
        self.old_state = self.state
        self.state = state

    def is_entry(self):
        return self.state != self.old_state

    def exec(self, c):
        if self.state == StreamParser.PARSER_WAITING:
            # Transitions
            if c == sym['STX']:
                self.frame = []
                self.status = StreamParser.FRAME_UNAVAILABLE
                self.set_state(StreamParser.PARSER_RECEIVING)
            else:
                self.set_state(self.state)
        elif self.state == StreamParser.PARSER_RECEIVING:
            # Transitions
            if c == sym['ETX']:
                self.status = StreamParser.FRAME_COMPLETE
                self.set_state(StreamParser.PARSER_WAITING)
            elif c == sym['EOT']:
                self.status = StreamParser.FRAME_TRUNCATED
                self.set_state(StreamParser.PARSER_WAITING)
            else:
                self.frame.append(c)
                self.status = StreamParser.FRAME_UNAVAILABLE
                self.set_state(self.state)
        return self.status


class FrameParser:
    """Parse a frame into data groups."""
    # Parser states
    PARSER_WAITING = 0
    PARSER_READING_LABEL = 1
    PARSER_READING_DATA = 2
    PARSER_READING_CHECKSUM = 3
    # Group status
    GROUP_AVAILABLE = 0
    GROUP_UNAVAILABLE = 1

    def __init__(self):
        self.state = FrameParser.PARSER_WAITING
        self.old_state = FrameParser.PARSER_WAITING
        self.group = None
        self.status = FrameParser.GROUP_UNAVAILABLE

    def set_state(self, state):
        self.old_state = self.state
        self.state = state

    def exec(self, c):
        if self.state == FrameParser.PARSER_WAITING:
            # Transitions
            if c == sym['LF']:
                self.status = FrameParser.GROUP_UNAVAILABLE
                self.group = dict()
                self.group['label'] = ""
                self.group['checkfield'] = []
                self.set_state(FrameParser.PARSER_READING_LABEL)
            else:
                self.set_state(self.state)
        elif self.state == FrameParser.PARSER_READING_LABEL:
            self.group['checkfield'].append(c)
            # Transitions
            if c == sym['SP']:
                self.group['data'] = ""
                self.set_state(FrameParser.PARSER_READING_DATA)
            else:
                self.group['label'] += chr(c)
                self.set_state(self.state)
        elif self.state == FrameParser.PARSER_READING_DATA:
            # Transitions
            if c == sym['SP']:
                self.group['checksum'] = ""
                self.set_state(FrameParser.PARSER_READING_CHECKSUM)
            else:
                self.group['data'] += chr(c)
                self.group['checkfield'].append(c)
                self.set_state(self.state)
        elif self.state == FrameParser.PARSER_READING_CHECKSUM:
            # Transitions
            if c == sym['CR']:
                self.status = FrameParser.GROUP_AVAILABLE
                self.set_state(FrameParser.PARSER_WAITING)
            else:
                self.group['checksum'] += chr(c)
                self.set_state(self.state)
        return self.status


class DataFormatter:
    @staticmethod
    def format(groups):
        res = dict()
        for g in groups:
            res[g['label']] = dict()
            res[g['label']]['data'] = g['data']
            res[g['label']]['valid'] = DataFormatter.check(g)
        return res

    @staticmethod
    def check(group):
        return group['checksum'] == chr((sum(group['checkfield']) & 0x3F) + 0x20)


class Tic:
    def __init__(self, params):
        self.prm = params
        self.uart = pyb.UART(6, self.prm['baudrate'])
        self.uart.init(self.prm['baudrate'], bits=self.prm['bits'], parity=self.prm['parity'], stop=self.prm['stop'])
        self.timeout = 3000  # ms

    def get_frame(self):
        sp = StreamParser()
        start = pyb.millis()
        while pyb.millis() - start < self.timeout:
            c = self.uart.readchar()
            if c != -1:
                status = sp.exec(c)
                if status == StreamParser.FRAME_COMPLETE:
                    return DataFormatter.format(Tic.get_groups(sp.frame))
        return

    @staticmethod
    def get_groups(frame):
        fp = FrameParser()
        groups = []
        for c in frame:
            status = fp.exec(c)
            if status == FrameParser.GROUP_AVAILABLE:
                groups.append(fp.group)
        return groups


def main(timeout):
    tic = Tic(cfg['historic'])
    start = pyb.millis()
    frames = []
    while pyb.millis() - start < timeout:
        frame = tic.get_frame()
        if frame is not None:
            frames.append(frame)
            print(frame)
    with open("json.txt", "w") as f:
        for frame in frames:
            f.write(ujson.dumps(frame) + '\n')


timeout = 100e3
main(timeout)
