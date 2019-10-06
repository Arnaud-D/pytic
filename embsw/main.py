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
TIMEOUT = 3600*1e3  # maximum execution time (ms)
OUTPUT_FILE = "data.json"

# Diode for data availability
DATA_AVAILABLE_LED = machine.Pin.board.LED_GREEN

# Diode for frame reception
FRAME_RECEIVED_LED = machine.Pin.board.LED_BLUE
FRAME_RECEIVED_PULSE_PERIOD = 100

# Diode for errors
ERROR_LED = machine.Pin.board.LED_RED

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

# Queues for data exchange between asynchronous tasks
chars = aqueues.Queue()
frames = aqueues.Queue()
processed_frames = aqueues.Queue()
lines = aqueues.Queue()

# Signal to stop shared between tasks
running = True


async def produce_chars(params):
    """Produces chars from the TIC interface."""
    tic = pyb.UART(6, params['baudrate'])
    tic.init(params['baudrate'], bits=params['bits'], parity=params['parity'], stop=params['stop'])
    reader = asyncio.StreamReader(tic)
    while running:
        data = await reader.read()
        for d in data:
            chars.put_nowait(d)


async def pulse_led(led, period):
    led.on()
    await asyncio.sleep_ms(period)
    led.off()


async def produce_frames():
    """Consume chars and produces frames."""
    frame = []
    parser_state = PARSER_WAITING_FRAME
    while running:
        c = await chars.get()
        if parser_state == PARSER_WAITING_FRAME:
            if c == STX:
                frame = []
                parser_state = PARSER_RECEIVING_FRAME
        elif parser_state == PARSER_RECEIVING_FRAME:
            if c == ETX:
                frames.put_nowait((frame, FRAME_COMPLETE))
                asyncio.ensure_future(pulse_led(FRAME_RECEIVED_LED, FRAME_RECEIVED_PULSE_PERIOD))
                parser_state = PARSER_WAITING_FRAME
            elif c == EOT:
                frames.put_nowait((frame, FRAME_TRUNCATED))
                asyncio.ensure_future(pulse_led(FRAME_RECEIVED_LED, FRAME_RECEIVED_PULSE_PERIOD))
                parser_state = PARSER_WAITING_FRAME
            else:
                frame.append(c)


async def process_frames():
    """Consumes frames and produces lines."""
    while running:
        frame, status = await frames.get()
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
            processed_frames.put_nowait(groups)


def checksum(group):
    """Compute the checksum for a data group."""
    return group['checksum'] == chr((sum(group['checkfield']) & 0x3F) + 0x20)


async def lineify():
    """Consume processed frames and produces lines."""
    while running:
        processed_frame = await processed_frames.get()
        reformatted_frame = dict()
        for group in processed_frame:
            reformatted_frame[group['label']] = dict()
            reformatted_frame[group['label']]['data'] = group['data']
            reformatted_frame[group['label']]['valid'] = checksum(group)
        line = ujson.dumps(reformatted_frame)
        lines.put_nowait(line)


async def write_lines(output_file, timeout):
    """Write lines from the writing queue to the output file."""
    global running
    DATA_AVAILABLE_LED.off()
    with open(output_file, "w") as f:
        start = pyb.millis()
        while pyb.elapsed_millis(start) < timeout:  # Consume lines until timeout
            line = await lines.get()
            f.write(line + '\n')
            print(line)
    DATA_AVAILABLE_LED.on()
    running = False


def main():
    pyb.freq(84000000, 84000000, 21000000, 42000000)
    ERROR_LED.off()
    loop = asyncio.get_event_loop()
    loop.create_task(produce_chars(CFG))
    loop.create_task(produce_frames())
    loop.create_task(process_frames())
    loop.create_task(lineify())
    loop.create_task(write_lines(OUTPUT_FILE, TIMEOUT))
    loop.run_forever()


if __name__ == "__main__":
    if OUTPUT_FILE in os.listdir():
        pyb.usb_mode('VCP+MSC')  # data file exists, connect to computer as mass storage
    else:
        pyb.usb_mode('VCP')  # only virtual COM port
        main()
