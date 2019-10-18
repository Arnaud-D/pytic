import pyb
import machine
import uasyncio as asyncio
import uasyncio.queues as aqueues
import ujson
import os

# Processing pipeline:
# TIC -->[produce_chars]--> chars -->[produce_frames]--> frames -->[process_frame]--> processed_frames
# -->[lineify]--> lines --> [write_lines]--> file

# TIC parameters sets
historic_params = {'baudrate': 1200,
                   'bits': 7,
                   'parity': 0,
                   'stop': 1,
                   }
standard_params = {'baudrate': 9600,
                   'bits': 7,
                   'parity': 0,
                   'stop': 1,
                   }

# TIC configuration
CFG = historic_params
OUTPUT_FILE = "data.json"

# Diode for data availability
DATA_AVAILABLE_LED = machine.Pin.board.LED_GREEN

# Diode for frame reception
FRAME_RECEIVED_LED = machine.Pin.board.LED_BLUE
FRAME_RECEIVED_PULSE_PERIOD = 100

# Diode for recording
RECORDING_LED = machine.Pin.board.LED_RED

# UART channel to use
UART_CHANNEL = 3

# Special symbols
STX = 0x02
ETX = 0x03
EOT = 0x04
LF = 0x0A
CR = 0x0D
SP = 0x20

# Stream parser -- States
PARSER_WAITING_FRAME = 0
PARSER_RECEIVING_FRAME = 1

# Stream parser -- Frame statuses
FRAME_COMPLETE = 0
FRAME_TRUNCATED = 1

# Frame parser -- States
PARSER_WAITING_GROUP = 0
PARSER_READING_LABEL = 1
PARSER_READING_DATA = 2
PARSER_READING_CHECKSUM = 3

# State manager states
DEVICE_PAUSED = 0
DEVICE_RECORDING = 1
DEVICE_STARTING = 2
DEVICE_PAUSING = 3

# Switch states
SWITCH_PRESSED = True
SWITCH_RELEASED = False

# Switch debounce time
BUTTON_DEBOUNCE = 50  # (ms)

# Queues for data exchange between asynchronous tasks
chars = aqueues.Queue()
frames = aqueues.Queue()
processed_frames = aqueues.Queue()
lines = aqueues.Queue()

# Events to tell the state machine to start or stop recording
button_pressed = False

# Function activation request/status
FUNCTION_OFF = False
FUNCTION_ON = True

# Function activations request
produce_chars_active_req = False
produce_frames_active_req = False
format_frames_active_req = False
produce_lines_active_req = False
write_lines_active_req = False

# Function activation status
produce_chars_active = False
produce_frames_active = False
format_frames_active = False
produce_lines_active = False
write_lines_active = False

# Sleep time for inactivity
SLEEP_TIME_INACTIVE = 50  # (ms)
SLEEP_TIME_ACTIVE = 10  # (ms)


async def pulse_led(led, period):
    """Pulse a LED once."""
    led.on()
    await asyncio.sleep_ms(period)
    led.off()


def checksum(group):
    """Compute the checksum for a data group."""
    return group['checksum'] == chr((sum(group['checkfield']) & 0x3F) + 0x20)


async def detect_button_press():
    """Detect a press on the USR button."""
    global button_pressed
    button = pyb.Switch()
    previous_state = button.value()
    current_state = previous_state
    while True:
        if current_state != previous_state and current_state == SWITCH_PRESSED:
            button_pressed = True
        previous_state = current_state
        current_state = button.value()
        await asyncio.sleep_ms(BUTTON_DEBOUNCE)


async def manage_device_state():
    """Manage the state of the device (recording/paused)."""
    # Inputs
    global button_pressed
    # Outputs
    global produce_chars_active_req
    global produce_frames_active_req
    global format_frames_active_req
    global produce_lines_active_req
    global write_lines_active_req
    # State
    recorder_state = DEVICE_PAUSED
    while True:
        if recorder_state == DEVICE_PAUSED:
            RECORDING_LED.off()
            if button_pressed:
                recorder_state = DEVICE_STARTING
        elif recorder_state == DEVICE_RECORDING:
            RECORDING_LED.on()
            if button_pressed:
                recorder_state = DEVICE_PAUSING
        elif recorder_state == DEVICE_STARTING:
            produce_chars_active_req = FUNCTION_ON
            produce_frames_active_req = FUNCTION_ON
            format_frames_active_req = FUNCTION_ON
            produce_lines_active_req = FUNCTION_ON
            write_lines_active_req = FUNCTION_ON
            if produce_chars_active_req == produce_chars_active \
               and produce_frames_active_req == produce_frames_active \
               and format_frames_active_req == format_frames_active \
               and produce_lines_active_req == produce_lines_active \
               and write_lines_active_req == write_lines_active:
                recorder_state = DEVICE_RECORDING
                button_pressed = False
        elif recorder_state == DEVICE_PAUSING:
            produce_chars_active_req = FUNCTION_OFF
            produce_frames_active_req = FUNCTION_OFF
            format_frames_active_req = FUNCTION_OFF
            produce_lines_active_req = FUNCTION_OFF
            write_lines_active_req = FUNCTION_OFF
            if produce_chars_active_req == produce_chars_active \
               and produce_frames_active_req == produce_frames_active \
               and format_frames_active_req == format_frames_active \
               and produce_lines_active_req == produce_lines_active \
               and write_lines_active_req == write_lines_active:
                recorder_state = DEVICE_PAUSED
                button_pressed = False
        else:
            print("Error.")
        await asyncio.sleep_ms(SLEEP_TIME_ACTIVE)


async def produce_chars(params):
    # Inputs
    global produce_chars_active_req
    # Outputs
    global chars
    global produce_chars_active
    """Produces chars from the TIC interface."""
    tic = pyb.UART(UART_CHANNEL, params['baudrate'])

    def tic_init():
        tic.init(params['baudrate'], bits=params['bits'], parity=params['parity'], stop=params['stop'])
    prev = not produce_chars_active_req
    tic_init()
    while True:
        if produce_chars_active_req == FUNCTION_ON:
            if prev != produce_chars_active_req:
                tic_init()
            produce_chars_active = FUNCTION_ON
            data = tic.read()
            if data is not None:
                for d in data:
                    chars.put_nowait(d)
            prev = produce_chars_active_req
            await asyncio.sleep_ms(SLEEP_TIME_ACTIVE)
        else:
            if prev != produce_chars_active_req:
                tic.deinit()
            produce_chars_active = FUNCTION_OFF
            chars = aqueues.Queue()  # empty output queue
            prev = produce_chars_active_req
            await asyncio.sleep_ms(SLEEP_TIME_INACTIVE)


async def produce_frames():
    """Consume chars and produces frames."""
    # Inputs
    global produce_frames_active_req
    # Outputs
    global frames
    global produce_frames_active
    # State
    frame = []
    parser_state = PARSER_WAITING_FRAME
    start = pyb.millis()
    while True:
        if produce_frames_active_req == FUNCTION_ON:
            produce_frames_active = FUNCTION_ON
            try:
                c = chars.get_nowait()
            except aqueues.QueueEmpty:
                await asyncio.sleep_ms(SLEEP_TIME_ACTIVE)
            else:
                if parser_state == PARSER_WAITING_FRAME:
                    if c == STX:
                        frame = []
                        parser_state = PARSER_RECEIVING_FRAME
                elif parser_state == PARSER_RECEIVING_FRAME:
                    if c == ETX or c == EOT:
                        frame_status = FRAME_COMPLETE if c == ETX else FRAME_TRUNCATED
                        timestamp = pyb.elapsed_millis(start)
                        frames.put_nowait((frame, frame_status, timestamp))
                        asyncio.get_event_loop().call_soon(pulse_led(FRAME_RECEIVED_LED, FRAME_RECEIVED_PULSE_PERIOD))
                        parser_state = PARSER_WAITING_FRAME
                    else:
                        frame.append(c)
                else:
                    print("Error")
        else:
            produce_frames_active = FUNCTION_OFF
            # empty output queue
            frames = aqueues.Queue()
            # reset parser state
            frame = []
            parser_state = PARSER_WAITING_FRAME
            # wait before checking activity again
            await asyncio.sleep_ms(SLEEP_TIME_INACTIVE)


async def format_frames():
    """Consumes frames and produces formatted frames."""
    # Inputs
    global format_frames_active_req
    # Outputs
    global processed_frames
    global format_frames_active
    while True:
        if format_frames_active_req == FUNCTION_ON:
            format_frames_active = FUNCTION_ON
            try:
                frame, status, timestamp = frames.get_nowait()
            except aqueues.QueueEmpty:
                await asyncio.sleep_ms(SLEEP_TIME_ACTIVE)
            else:
                if status == FRAME_COMPLETE:
                    parser_state = PARSER_WAITING_GROUP
                    groups = []
                    group = dict()
                    for c in frame:
                        if parser_state == PARSER_WAITING_GROUP:
                            if c == LF:
                                group = dict()
                                group['label'] = ""
                                group['data'] = ""
                                group['checksum'] = ""
                                group['checkfield'] = []
                                parser_state = PARSER_READING_LABEL
                        elif parser_state == PARSER_READING_LABEL:
                            group['checkfield'].append(c)
                            if c == SP:
                                parser_state = PARSER_READING_DATA
                            else:
                                group['label'] += chr(c)
                        elif parser_state == PARSER_READING_DATA:
                            if c == SP:
                                parser_state = PARSER_READING_CHECKSUM
                            else:
                                group['data'] += chr(c)
                                group['checkfield'].append(c)
                        elif parser_state == PARSER_READING_CHECKSUM:
                            if c == CR:
                                groups.append(group)
                                parser_state = PARSER_WAITING_GROUP
                            else:
                                group['checksum'] += chr(c)
                    processed_frames.put_nowait((groups, timestamp))
        else:
            format_frames_active = FUNCTION_OFF
            processed_frames = aqueues.Queue()  # empty output queue
            await asyncio.sleep_ms(SLEEP_TIME_INACTIVE)


async def produce_lines():
    """Consume formatted frames and produces lines."""
    # Inputs
    global produce_lines_active_req
    # Outputs
    global lines
    global produce_lines_active
    while True:
        if produce_lines_active_req == FUNCTION_ON:
            produce_lines_active = FUNCTION_ON
            try:
                processed_frame, timestamp = processed_frames.get_nowait()
            except aqueues.QueueEmpty:
                await asyncio.sleep_ms(SLEEP_TIME_ACTIVE)
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
                lines.put_nowait(line)
        else:
            produce_lines_active = FUNCTION_OFF
            lines = aqueues.Queue()  # empty output queue
            await asyncio.sleep_ms(SLEEP_TIME_INACTIVE)


async def write_lines(output_file):
    """Write lines from the writing queue to the output file."""
    # Input
    global write_lines_active_req
    # Outputs
    global write_lines_active
    f = None
    # State
    previously_active = write_lines_active_req
    while True:
        if write_lines_active_req == FUNCTION_ON:
            write_lines_active = FUNCTION_ON
            if write_lines_active_req != previously_active:
                f = open(output_file, "a")
            previously_active = write_lines_active_req
            try:
                line = lines.get_nowait()
            except aqueues.QueueEmpty:
                await asyncio.sleep_ms(SLEEP_TIME_ACTIVE)
            else:
                if f is not None:
                    f.write(line + '\n')
                    f.flush()
        else:
            write_lines_active = FUNCTION_OFF
            if write_lines_active_req != previously_active and f is not None:
                f.close()
            previously_active = write_lines_active_req
            await asyncio.sleep_ms(SLEEP_TIME_INACTIVE)


def main():
    loop = asyncio.get_event_loop()
    loop.create_task(manage_device_state())
    loop.create_task(detect_button_press())
    loop.create_task(produce_chars(CFG))
    loop.create_task(produce_frames())
    loop.create_task(format_frames())
    loop.create_task(produce_lines())
    loop.create_task(write_lines(OUTPUT_FILE))
    loop.run_forever()


if __name__ == "__main__":
    if OUTPUT_FILE in os.listdir():
        pyb.usb_mode('VCP+MSC')  # data file exists, connect to computer as mass storage
        DATA_AVAILABLE_LED.on()
    else:
        pyb.usb_mode('VCP')  # only virtual COM port
        main()
