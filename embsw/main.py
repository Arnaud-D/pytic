import pyb
import machine
import uasyncio as asyncio
import lib.aswitch as aswitch
import logger as log
import manager as mgr
import feedback as fb
import input

# Sleep time for inactivity
SLEEP_TIME_INACTIVE = 50  # (ms)
SLEEP_TIME_ACTIVE = 10  # (ms)

# Configuration
CFG = "historic"
OUTPUT_FILE = "data.json"
UART_CHANNEL = 3


def main():
    if pyb.usb_mode() == "MSC":  # Board started in "data transfer mode"
        fb.feedback_transfer_mode()
    else:  # Board started in "logger mode"
        logger_mode()


def logger_mode():
    logger = log.Logger(asyncio.get_event_loop(),
                        "reduced",
                        CFG,
                        UART_CHANNEL,
                        OUTPUT_FILE,
                        SLEEP_TIME_ACTIVE,
                        SLEEP_TIME_INACTIVE,
                        fb.feedback_reception)
    manager = mgr.Manager(logger,
                          SLEEP_TIME_ACTIVE,
                          fb.feedback_logger_mode,
                          fb.feedback_paused,
                          fb.feedback_started,
                          fb.feedback_stopped)
    loop = asyncio.get_event_loop()
    manager.schedule(loop)
    loop.create_task(input.detect_button_press(manager))
    button = aswitch.Pushbutton(machine.Pin.board.SW)
    button.long_func(lambda: input.callback_long_press(manager))
    loop.run_forever()


if __name__ == "__main__":
    main()
