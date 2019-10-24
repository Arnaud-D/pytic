import uasyncio as asyncio
import machine

# LED allocation
LED_TRANSFER_MODE = machine.Pin.board.LED_BLUE
LED_LOGGER_MODE = machine.Pin.board.LED_GREEN
LED_STATUS_STARTED = machine.Pin.board.LED_RED
LED_STATUS_STOPPED = machine.Pin.board.LED_YELLOW
LED_FRAME_RECEIVED = machine.Pin.board.LED_YELLOW


def feedback_transfer_mode():
    LED_TRANSFER_MODE.on()
    LED_LOGGER_MODE.off()
    LED_STATUS_STARTED.off()
    LED_STATUS_STOPPED.off()
    LED_FRAME_RECEIVED.off()


def feedback_logger_mode():
    LED_LOGGER_MODE.on()
    LED_TRANSFER_MODE.off()


def feedback_paused():
    LED_STATUS_STARTED.off()
    LED_STATUS_STOPPED.off()


def feedback_started():
    LED_STATUS_STARTED.on()
    LED_STATUS_STOPPED.off()


async def pulse_led(led, period):
    """Pulse a LED once."""
    led.on()
    await asyncio.sleep_ms(period)
    led.off()


def feedback_reception():
    pulse_duration = 100
    asyncio.get_event_loop().call_soon(pulse_led(LED_FRAME_RECEIVED, pulse_duration))


def feedback_stopped():
    LED_STATUS_STARTED.off()
    LED_STATUS_STOPPED.on()
