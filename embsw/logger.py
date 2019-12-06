import pyb
import uasyncio as asyncio


def create_reader(cfg, channel):
    if cfg == "historic":
        return HistoricReader(channel)
    elif cfg == "standard":
        return StandardReader(channel)
    else:
        raise ValueError("cfg is '{}' but is expected to be 'historic' or 'standard'.".format(cfg))


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

    # States of the stream parser
    SP_WAITING = 0
    SP_RECEIVING = 1

    def __init__(self):
        self.generator = None

    def init(self):
        self.generator = self.frame_generator()
        next(self.generator)

    def deinit(self):
        self.generator = None

    def parse(self, data_bytes):
        for byte in data_bytes:
            frame_data, is_frame_complete = self.generator.send(byte)
            if frame_data is not None:
                return frame_data, is_frame_complete
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
                    buffer = bytearray()
                    buffer.append(c)
                    state = Parser.SP_RECEIVING
            elif state == Parser.SP_RECEIVING:
                if c == Parser.SYM_ETX or c == Parser.SYM_EOT:
                    buffer.append(c)
                    frame_data, is_frame_complete = buffer, c == Parser.SYM_ETX
                    state = Parser.SP_WAITING
                else:
                    buffer.append(c)


class Writer:
    def __init__(self, filename_data, filename_time):
        self.filename_data = filename_data
        self.filename_time = filename_time
        self.file_data = None
        self.file_time = None
        self.initialized = False

    def init(self):
        """Initialize the writer."""
        self.file_data = open(self.filename_data, "ab")
        self.file_time = open(self.filename_time, "a")
        self.initialized = True

    def deinit(self):
        """Deinitialize the writer."""
        self.file_data.close()
        self.file_time.close()
        self.initialized = False

    def write(self, data, timestamp):
        """Write data to a file."""
        if self.initialized:
            self.file_data.write(data)
            self.file_data.flush()
            self.file_time.write(str(timestamp) + "\n")
            self.file_time.flush()
        else:
            print("Race condition occured...")


class Logger:
    def __init__(self, meter_mode, channel, filename_data, filename_time, active_wait_time, inactive_wait_time, on_reception):
        self.start = pyb.millis()
        self.on_reception = on_reception
        self.active = False
        self.active_wait_time = active_wait_time
        self.inactive_wait_time = inactive_wait_time
        self.parser = Parser()
        self.reader = create_reader(meter_mode, channel)
        self.writer = Writer(filename_data, filename_time)

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
                    # TODO: correct race condition where file is closed when awaiting and then write is attempted
                    self.writer.write(frame_data, timestamp)
                await asyncio.sleep_ms(self.active_wait_time)
            else:
                await asyncio.sleep_ms(self.inactive_wait_time)
