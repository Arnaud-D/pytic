import pyb
import uasyncio as asyncio

# Switch states
SWITCH_PRESSED = True
SWITCH_RELEASED = False

BUTTON_DEBOUNCE = 50  # Switch debounce duration (ms)
BUTTON_LONGPRESS = 1000  # Long press duration (ms)


def callback_long_press(manager):
    """Callback on detection of long press of the button."""
    manager.notify_long_press()


async def detect_button_press(manager):
    """Detect a press on the USR button."""
    button = pyb.Switch()
    previous_state = button.value()
    current_state = previous_state
    while True:
        if current_state != previous_state and current_state == SWITCH_PRESSED:
            manager.notify_short_press()
        previous_state = current_state
        current_state = button.value()
        await asyncio.sleep_ms(BUTTON_DEBOUNCE)
