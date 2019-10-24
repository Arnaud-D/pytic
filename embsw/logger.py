import pyb
import uasyncio as asyncio
import uasyncio.queues as aqueues
import ujson

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
FP_WAITING_GROUP = 0
FP_READING_LABEL = 1
FP_READING_DATA = 2
FP_READING_CHECKSUM = 3

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
    return group['checksum'] == chr((sum(group['checkfield']) & 0x3F) + 0x20)


class Logger:
    def __init__(self, cfg, channel, filename, active_wait_time, inactive_wait_time, on_reception):
        if cfg == "historic":
            self._cfg = CFG_HISTORIC
        elif cfg == "standard":
            self._cfg = CFG_STANDARD
        else:
            raise ValueError("'{}' is not a correct value for argument cfg.".format(cfg))

        self._channel = channel
        self._filename = filename

        # Queues for data exchange between asynchronous tasks
        self._chars = aqueues.Queue()
        self._frames = aqueues.Queue()
        self._processed_frames = aqueues.Queue()
        self._lines = aqueues.Queue()

        # Logger activation request
        self._activation_requested = False

        # Function activation statuses
        self._produce_chars_active = False
        self._produce_frames_active = False
        self._format_frames_active = False
        self._produce_lines_active = False
        self._write_lines_active = False

        # Wait times
        self.active_wait_time = active_wait_time
        self.inactive_wait_time = inactive_wait_time

        # Callback on frame reception
        self.on_reception = on_reception

    def activate(self):
        """Request the activation of the logger."""
        self._activation_requested = True

    def deactivate(self):
        """Request the deactivation of the logger."""
        self._activation_requested = False

    def status(self):
        """Return the status of the logger (active, inactive, activating, deactivating)."""
        if self._activation_requested:
            if self._produce_chars_active \
               and self._produce_frames_active \
               and self._format_frames_active \
               and self._produce_lines_active \
               and self._write_lines_active:
                return LOGGER_ACTIVE
            else:
                return LOGGER_ACTIVATING
        else:
            if not self._produce_chars_active \
               and not self._produce_frames_active \
               and not self._format_frames_active \
               and not self._produce_lines_active \
               and not self._write_lines_active:
                return LOGGER_INACTIVE
            else:
                return LOGGER_DEACTIVATING

    async def produce_chars(self):
        """Produces chars from the TIC interface."""
        tic = pyb.UART(self._channel, self._cfg['baudrate'])

        def tic_init():
            tic.init(self._cfg['baudrate'],
                     bits=self._cfg['bits'],
                     parity=self._cfg['parity'],
                     stop=self._cfg['stop'])
        prev = not self._activation_requested
        tic_init()
        while True:
            if self._activation_requested:
                if prev != self._activation_requested:
                    tic_init()
                self._produce_chars_active = True
                data = tic.read()
                if data is not None:
                    for d in data:
                        self._chars.put_nowait(d)
                prev = self._activation_requested
                await asyncio.sleep_ms(self.active_wait_time)
            else:
                if prev != self._activation_requested:
                    tic.deinit()
                self._produce_chars_active = False
                self._chars = aqueues.Queue()  # empty output queue
                prev = self._activation_requested
                await asyncio.sleep_ms(self.inactive_wait_time)

    async def produce_frames(self):
        """Consume chars and produces frames."""
        frame = []
        parser_state = SP_WAITING
        start = pyb.millis()
        while True:
            if self._activation_requested:
                self._produce_frames_active = True
                try:
                    c = self._chars.get_nowait()
                except aqueues.QueueEmpty:
                    await asyncio.sleep_ms(self.active_wait_time)
                else:
                    if parser_state == SP_WAITING:
                        if c == SYM_STX:
                            frame = []
                            parser_state = SP_RECEIVING
                    elif parser_state == SP_RECEIVING:
                        if c == SYM_ETX or c == SYM_EOT:
                            frame_status = FRAME_COMPLETE if c == SYM_ETX else FRAME_TRUNCATED
                            timestamp = pyb.elapsed_millis(start)
                            self._frames.put_nowait((frame, frame_status, timestamp))
                            self.on_reception()
                            parser_state = SP_WAITING
                        else:
                            frame.append(c)
                    else:
                        print("Error")
            else:
                self._produce_frames_active = False
                self._frames = aqueues.Queue()
                frame = []
                parser_state = SP_WAITING
                await asyncio.sleep_ms(self.inactive_wait_time)

    async def format_frames(self):
        """Consumes frames and produces formatted frames."""
        while True:
            if self._activation_requested:
                self._format_frames_active = True
                try:
                    frame, status, timestamp = self._frames.get_nowait()
                except aqueues.QueueEmpty:
                    await asyncio.sleep_ms(self.active_wait_time)
                else:
                    if status == FRAME_COMPLETE:
                        parser_state = FP_WAITING_GROUP
                        groups = []
                        group = dict()
                        for c in frame:
                            if parser_state == FP_WAITING_GROUP:
                                if c == SYM_LF:
                                    group = dict()
                                    group['label'] = ""
                                    group['data'] = ""
                                    group['checksum'] = ""
                                    group['checkfield'] = []
                                    parser_state = FP_READING_LABEL
                            elif parser_state == FP_READING_LABEL:
                                group['checkfield'].append(c)
                                if c == SYM_SP:
                                    parser_state = FP_READING_DATA
                                else:
                                    group['label'] += chr(c)
                            elif parser_state == FP_READING_DATA:
                                if c == SYM_SP:
                                    parser_state = FP_READING_CHECKSUM
                                else:
                                    group['data'] += chr(c)
                                    group['checkfield'].append(c)
                            elif parser_state == FP_READING_CHECKSUM:
                                if c == SYM_CR:
                                    groups.append(group)
                                    parser_state = FP_WAITING_GROUP
                                else:
                                    group['checksum'] += chr(c)
                        self._processed_frames.put_nowait((groups, timestamp))
            else:
                self._format_frames_active = False
                self._processed_frames = aqueues.Queue()  # empty output queue
                await asyncio.sleep_ms(self.inactive_wait_time)

    async def produce_lines(self):
        """Consume formatted frames and produces lines."""
        while True:
            if self._activation_requested:
                self._produce_lines_active = True
                try:
                    processed_frame, timestamp = self._processed_frames.get_nowait()
                except aqueues.QueueEmpty:
                    await asyncio.sleep_ms(self.active_wait_time)
                else:
                    reformatted_frame = dict()
                    reformatted_frame['timestamp'] = dict()
                    reformatted_frame['timestamp']['data'] = timestamp
                    reformatted_frame['timestamp']['valid'] = True
                    for group in processed_frame:
                        reformatted_frame[group['label']] = dict()
                        reformatted_frame[group['label']]['data'] = group['data']
                        reformatted_frame[group['label']]['valid'] = checksum(group)
                    line = ujson.dumps(reformatted_frame)
                    self._lines.put_nowait(line)
            else:
                self._produce_lines_active = False
                self._lines = aqueues.Queue()  # empty output queue
                await asyncio.sleep_ms(self.inactive_wait_time)

    async def write_lines(self):
        """Write lines from the writing queue to the output file."""
        file = None
        previously_active = self._activation_requested
        while True:
            if self._activation_requested:
                self._write_lines_active = True
                if self._activation_requested != previously_active:
                    file = open(self._filename, "a")
                previously_active = self._activation_requested
                try:
                    line = self._lines.get_nowait()
                except aqueues.QueueEmpty:
                    await asyncio.sleep_ms(self.active_wait_time)
                else:
                    if file is not None:
                        file.write(line + "\n")
                        file.flush()
            else:
                self._write_lines_active = False
                if self._activation_requested != previously_active and file is not None:
                    file.close()
                previously_active = self._activation_requested
                await asyncio.sleep_ms(self.inactive_wait_time)

    def schedule(self, loop):
        loop.create_task(self.produce_chars())
        loop.create_task(self.produce_frames())
        loop.create_task(self.format_frames())
        loop.create_task(self.produce_lines())
        loop.create_task(self.write_lines())
