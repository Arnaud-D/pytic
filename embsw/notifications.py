import uasyncio as asyncio
import machine

LED_DEVICE_TRANSFERRING = machine.Pin.board.LED_BLUE
LED_DEVICE_LOGGING = machine.Pin.board.LED_GREEN
LED_LOGGER_STARTED = machine.Pin.board.LED_RED
LED_LOGGER_STOPPED = machine.Pin.board.LED_YELLOW
LED_FRAME_RECEPTION = machine.Pin.board.LED_YELLOW


def device_transferring():
    LED_DEVICE_TRANSFERRING.on()
    LED_DEVICE_LOGGING.off()
    LED_LOGGER_STARTED.off()
    LED_LOGGER_STOPPED.off()
    LED_FRAME_RECEPTION.off()


def device_logging():
    LED_DEVICE_LOGGING.on()
    LED_DEVICE_TRANSFERRING.off()


def logger_paused():
    LED_LOGGER_STARTED.off()
    LED_LOGGER_STOPPED.off()


def logger_started():
    LED_LOGGER_STARTED.on()
    LED_LOGGER_STOPPED.off()


def device_stopped():
    LED_LOGGER_STARTED.off()
    LED_LOGGER_STOPPED.on()


async def pulse_led(led, period):
    """Pulse a LED once."""
    led.on()
    await asyncio.sleep_ms(period)
    led.off()


def frame_received():
    pulse_duration = 100
    asyncio.get_event_loop().call_soon(pulse_led(LED_FRAME_RECEPTION, pulse_duration))
