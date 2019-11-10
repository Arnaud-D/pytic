import pyb
import uasyncio as asyncio
import manager

# Switch states
SWITCH_PRESSED = True
SWITCH_RELEASED = False

BUTTON_DEBOUNCE = 20  # Switch debounce duration (ms)
BUTTON_LONGPRESS = 1000  # Long press duration (ms)


def callback_long_press(mgr):
    """Callback on detection of long press of the button."""
    mgr.notify(manager.Event.EVENT2)


async def detect_button_press(mgr):
    """Detect a press on the USR button."""
    button = pyb.Switch()
    previous_state = button.value()
    current_state = previous_state
    while True:
        if current_state != previous_state and current_state == SWITCH_PRESSED:
            mgr.notify(manager.Event.EVENT1)
        previous_state = current_state
        current_state = button.value()
        await asyncio.sleep_ms(BUTTON_DEBOUNCE)
