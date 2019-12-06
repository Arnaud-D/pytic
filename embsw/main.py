import pyb
import machine
import uasyncio as asyncio
import lib.aswitch as aswitch
import logger
import manager
import notifications
import input

# Sleep time for inactivity
SLEEP_TIME_INACTIVE = 50  # (ms)
SLEEP_TIME_ACTIVE = 10  # (ms)

# Configuration
METER_MODE = "historic"
OUTPUT_FILE_DATA = "data.txt"
OUTPUT_FILE_TIME = "time.txt"
UART_CHANNEL = 3


def main():
    if pyb.usb_mode() == "MSC":  # Board started in "data transfer mode"
        notifications.device_transferring()
    else:  # Board started in "logger mode"
        logger_mode()


def logger_mode():
    log = logger.Logger(METER_MODE,
                        UART_CHANNEL,
                        OUTPUT_FILE_DATA,
                        OUTPUT_FILE_TIME,
                        SLEEP_TIME_ACTIVE,
                        SLEEP_TIME_INACTIVE,
                        notifications.frame_received)
    mgr = manager.Manager(log,
                          SLEEP_TIME_ACTIVE,
                          notifications.device_logging,
                          notifications.logger_paused,
                          notifications.logger_started,
                          notifications.device_stopped)
    button = aswitch.Pushbutton(machine.Pin.board.SW)
    button.long_func(lambda: input.callback_long_press(mgr))

    loop = asyncio.get_event_loop()
    loop.create_task(log.log())
    loop.create_task(mgr.execute())
    loop.create_task(input.detect_button_press(mgr))
    loop.create_task(button.buttoncheck())
    loop.run_forever()


if __name__ == "__main__":
    main()
