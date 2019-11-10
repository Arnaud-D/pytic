import pyb
import uasyncio as asyncio
import ujson
import ure


class Reader:
    def __init__(self, channel, baudrate, bits, parity, stop):
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop = stop
        self.uart = pyb.UART(channel, baudrate)
        self.stream_reader = asyncio.StreamReader(self.uart)
        self.read = self.stream_reader.read

    def init(self):
        self.uart.init(self.baudrate, bits=self.bits, parity=self.parity, stop=self.stop)

    def deinit(self):
        self.uart.deinit()


class HistoricReader(Reader):
    def __init__(self, channel):
        super().__init__(channel=channel, baudrate=1200, bits=7, parity=0, stop=1)


class StandardReader(Reader):
    def __init__(self, channel):
        super().__init__(channel=channel, baudrate=9600, bits=7, parity=0, stop=1)


class Parser:
    # Special symbols
    SYM_STX = 0x02
    SYM_ETX = 0x03
    SYM_EOT = 0x04
    SYM_LF = 0x0A
    SYM_CR = 0x0D
    SYM_SP = 0x20

    # States of the stream parser
    SP_WAITING = 0
    SP_RECEIVING = 1

    def __init__(self, regex_payload, regex_check):
        self.generator = None
        self.regex_payload = ure.compile(regex_payload)
        self.regex_check = ure.compile(regex_check)

    def init(self):
        self.generator = self.frame_generator()
        next(self.generator)

    def deinit(self):
        self.generator = None

    def parse(self, data_bytes):
        for byte in data_bytes:
            frame_data, is_frame_complete = self.generator.send(byte)
            if frame_data is not None and is_frame_complete:
                return self.extract_groups(frame_data), is_frame_complete
        return None, None

    @staticmethod
    def frame_generator():
        """Generate frames (list of bytes) from received bytes."""
        state = Parser.SP_WAITING
        frame_data, is_frame_complete = None, None
        buffer = []
        while True:
            c = yield frame_data, is_frame_complete
            frame_data, is_frame_complete = None, None
            if state == Parser.SP_WAITING:
                if c == Parser.SYM_STX:
                    buffer = []
                    state = Parser.SP_RECEIVING
            elif state == Parser.SP_RECEIVING:
                if c == Parser.SYM_ETX or c == Parser.SYM_EOT:
                    frame_data, is_frame_complete = buffer, c == Parser.SYM_ETX
                    state = Parser.SP_WAITING
                else:
                    buffer.append(c)

    def extract_groups(self, frame):
        """Parse a frame to extract the groups."""
        groups = []
        buffer = ""
        for c in frame:
            if c == Parser.SYM_LF:
                buffer = ""
            elif c == Parser.SYM_CR:
                match_payload = self.regex_payload.match(buffer)
                match_check = self.regex_check.match(buffer)
                group = {'label': match_payload.group(1),
                         'data': match_payload.group(2),
                         'checkfield': match_check.group(1),
                         'checksum': match_check.group(2)}
                groups.append(group)
            else:
                buffer += chr(c)
        return groups


class HistoricParser(Parser):
    def __init__(self):
        super().__init__(regex_payload="([^ ]+) (.+) .", regex_check="(.+) (.)")


class StandardParser(Parser):
    def __init__(self):
        super().__init__(regex_payload="([^ ]+) (.+) .", regex_check="(.+) (.)")  # TODO: adapt for standard mode


class Formatter:
    @staticmethod
    def format(groups, is_frame_complete, timestamp):
        raise NotImplementedError


class JsonFormatter(Formatter):
    @staticmethod
    def format(groups, is_frame_complete, timestamp):
        """Produce a line from a processed frame with timestamp (full information)."""
        reformatted_frame = dict()
        reformatted_frame['timestamp'] = {'data': timestamp, 'valid': True}
        for group in groups:
            reformatted_frame[group['label']] = {'data': group['data'], 'valid': checksum(group)}
        line = ujson.dumps(reformatted_frame) + "\n"
        return line


class CsvFormatter(Formatter):
    @staticmethod
    def format(groups, is_frame_complete, timestamp):
        """Make a line from a processed frame with timestamp (reduced information)."""
        reformatted_frame = dict()
        reformatted_frame['timestamp'] = {'data': timestamp, 'valid': True}
        for group in groups:
            reformatted_frame[group['label']] = {'data': group['data'], 'valid': checksum(group)}
        reduced_frame = dict()
        all_valid = True
        for label in ['timestamp', 'BASE', 'PAPP']:
            reduced_frame[label] = int(reformatted_frame[label]['data'])
            all_valid = all_valid and reformatted_frame[label]['valid']
        line = "{}, {}, {}\n".format(reduced_frame['timestamp'], reduced_frame['BASE'], reduced_frame['PAPP'])
        if all_valid:
            return line


class Writer:
    def __init__(self, filename):
        self.filename = filename
        self.file = None

    def init(self):
        """Initialize the writer."""
        self.file = open(self.filename, "a")

    def deinit(self):
        """Deinitialize the writer."""
        self.file.close()

    def write(self, data):
        """Write data to a file."""
        self.file.write(data)
        self.file.flush()


def checksum(group):
    """Compute the checksum for a data group."""
    return group['checksum'] == chr((sum([ord(c) for c in group['checkfield']]) & 0x3F) + 0x20)


class Logger:
    def __init__(self, logtype, cfg, channel, filename, active_wait_time, inactive_wait_time, on_reception):
        self.start = pyb.millis()
        self.on_reception = on_reception
        self.active = False
        self.active_wait_time = active_wait_time
        self.inactive_wait_time = inactive_wait_time

        # Select reader and parser type
        if cfg == "historic":
            self.reader = HistoricReader(channel)
            self.parser = HistoricParser()
        elif cfg == "standard":
            self.reader = StandardReader(channel)
            self.parser = StandardParser()
        else:
            raise ValueError("'{}' is not a correct value for argument cfg.".format(cfg))

        # Select formatter type
        if logtype == "json":
            self.formatter = JsonFormatter()
        elif logtype == "csv":
            self.formatter = CsvFormatter()
        else:
            raise ValueError("'{}' is not a correct value for argument logtype.".format(cfg))

        # Select writer type
        self.writer = Writer(filename)

    def activate(self):
        """Activate the logger."""
        self.active = True
        self.reader.init()
        self.parser.init()
        self.writer.init()

    def deactivate(self):
        """Deactivate the logger."""
        self.active = False
        self.reader.deinit()
        self.parser.deinit()
        self.writer.deinit()

    async def log(self):
        """Log the TIC interface."""
        while True:
            if self.active:
                data = await self.reader.read()
                frame_data, is_frame_complete = self.parser.parse(data)
                if frame_data is not None:  # Frame received
                    self.on_reception()
                    timestamp = pyb.elapsed_millis(self.start)
                    formatted_data = self.formatter.format(frame_data, is_frame_complete, timestamp)
                    self.writer.write(formatted_data)
                await asyncio.sleep_ms(self.active_wait_time)
            else:
                await asyncio.sleep_ms(self.inactive_wait_time)
