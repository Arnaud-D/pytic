import pyb
import uasyncio as asyncio
import uasyncio.queues as aqueues
import ujson
import ure

# Special symbols
SYM_STX = 0x02
SYM_ETX = 0x03
SYM_EOT = 0x04
SYM_LF = 0x0A
SYM_CR = 0x0D
SYM_SP = 0x20

# Sets of parameters for series communication
CFG_HISTORIC = {'baudrate': 1200,
                'bits': 7,
                'parity': 0,
                'stop': 1}
CFG_STANDARD = {'baudrate': 9600,
                'bits': 7,
                'parity': 0,
                'stop': 1}

# States of the stream parser
SP_WAITING = 0
SP_RECEIVING = 1

# Status of received frames
FRAME_COMPLETE = 0
FRAME_TRUNCATED = 1

# States of the frame parser
FP_WAITING = 0
FP_READING = 1

# Status of the logger
LOGGER_INACTIVE = 0
LOGGER_ACTIVE = 1
LOGGER_ACTIVATING = 2
LOGGER_DEACTIVATING = 3

# Processing pipeline:
# TIC -->[produce_chars]--> chars -->[produce_frames]--> frames -->[process_frame]--> processed_frames
# -->[lineify]--> lines --> [write_lines]--> file


def checksum(group):
    """Compute the checksum for a data group."""
    return group['checksum'] == chr((sum([ord(c) for c in group['checkfield']]) & 0x3F) + 0x20)


class Logger:
    def __init__(self, loop, logtype, cfg, channel, filename, active_wait_time, inactive_wait_time, on_reception):
        self.loop = loop
        loop.create_task(self.read_chars())
        loop.create_task(self.write_frames())
        if logtype == "full":
            self.make_line = self.make_line_full
        elif logtype == "reduced":
            self.make_line = self.make_line_reduced
        else:
            raise ValueError("'{}' is not a correct value for argument cfg.".format(cfg))

        if cfg == "historic":
            self.cfg = CFG_HISTORIC
            self.regex_payload = ure.compile("([^ ]+) (.+) .")
            self.regex_check = ure.compile("(.+) (.)")
        elif cfg == "standard":
            self.cfg = CFG_STANDARD
            self.regex_payload = ure.compile("([^ ]+) (.+) .")  # TODO: adapt for standard mode
            self.regex_check = ure.compile("(.+) (.)")  # TODO: adapt for standard mode
        else:
            raise ValueError("'{}' is not a correct value for argument cfg.".format(cfg))

        self.channel = channel
        self.filename = filename

        # Queue for data exchange between asynchronous tasks
        self.chars = aqueues.Queue()

        # Logger activation request
        self.activation_requested = False

        # Function activation statuses
        self.produce_chars_active = False
        self.write_frames_active = False

        # Wait times
        self.active_wait_time = active_wait_time
        self.inactive_wait_time = inactive_wait_time

        # Callback on frame reception
        self.on_reception = on_reception

    def activate(self):
        """Request the activation of the logger."""
        self.activation_requested = True

    def deactivate(self):
        """Request the deactivation of the logger."""
        self.activation_requested = False

    def status(self):
        """Return the status of the logger (active, inactive, activating, deactivating)."""
        if self.activation_requested:
            if self.produce_chars_active \
               and self.write_frames_active:
                return LOGGER_ACTIVE
            else:
                return LOGGER_ACTIVATING
        else:
            if not self.produce_chars_active \
               and not self.write_frames_active:
                return LOGGER_INACTIVE
            else:
                return LOGGER_DEACTIVATING

    async def read_chars(self):
        """Read chars from the TIC interface."""
        tic = pyb.UART(self.channel, self.cfg['baudrate'])

        def tic_init():
            tic.init(self.cfg['baudrate'],
                     bits=self.cfg['bits'],
                     parity=self.cfg['parity'],
                     stop=self.cfg['stop'])
        prev = not self.activation_requested
        tic_init()
        while True:
            if self.activation_requested:
                if prev != self.activation_requested:
                    tic_init()
                self.produce_chars_active = True
                data = tic.read()
                if data is not None:
                    for d in data:
                        self.chars.put_nowait(d)
                prev = self.activation_requested
                await asyncio.sleep_ms(self.active_wait_time)
            else:
                if prev != self.activation_requested:
                    tic.deinit()
                self.produce_chars_active = False
                self.chars = aqueues.Queue()
                prev = self.activation_requested
                await asyncio.sleep_ms(self.inactive_wait_time)

    async def write_frames(self):
        """Write frames to the file."""
        frame = []
        state = SP_WAITING
        start = pyb.millis()
        file = None
        while True:
            if self.activation_requested:
                self.write_frames_active = True
                if file is None:
                    file = open(self.filename, "a")
                try:
                    c = self.chars.get_nowait()
                except aqueues.QueueEmpty:
                    await asyncio.sleep_ms(self.active_wait_time)
                else:
                    if state == SP_WAITING:
                        if c == SYM_STX:
                            frame = []
                            state = SP_RECEIVING
                    elif state == SP_RECEIVING:
                        if c == SYM_ETX or c == SYM_EOT:
                            frame_status = FRAME_COMPLETE if c == SYM_ETX else FRAME_TRUNCATED
                            timestamp = pyb.elapsed_millis(start)
                            self.write_frame(file, frame, frame_status, timestamp)
                            self.on_reception()
                            state = SP_WAITING
                        else:
                            frame.append(c)
                    else:
                        print("Error")
            else:
                self.write_frames_active = False
                if file is not None:
                    file.close()
                    file = None
                frame = []
                state = SP_WAITING
                await asyncio.sleep_ms(self.inactive_wait_time)

    def write_frame(self, file, frame, status, timestamp):
        """Write a frame to a file."""
        groups = self.extract_groups(frame, status)
        line = self.make_line(groups, timestamp)
        self.write_line(file, line)

    def extract_groups(self, frame, status):
        """Parse a frame to extract the groups."""
        if status == FRAME_COMPLETE:  # Filter out truncated frames
            groups = []
            buffer = ""
            for c in frame:
                if c == SYM_LF:
                    buffer = ""
                elif c == SYM_CR:
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

    @staticmethod
    def make_line_full(groups, timestamp):
        """Produce a line from a processed frame with timestamp (full information)."""
        reformatted_frame = dict()
        reformatted_frame['timestamp'] = {'data': timestamp, 'valid': True}
        for group in groups:
            reformatted_frame[group['label']] = {'data': group['data'], 'valid': checksum(group)}
        line = ujson.dumps(reformatted_frame) + "\n"
        return line

    @staticmethod
    def make_line_reduced(groups, timestamp):
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

    @staticmethod
    def write_line(file, line):
        """Write a line to a file."""
        file.write(line)
        file.flush()
