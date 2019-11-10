import uasyncio as asyncio
import utoken

# States
PAUSED = 0
STARTED = 1
STOPPED = 2


class Manager:
    """Manage the state of the device (started/paused/stopped)."""

    def __init__(self, logger, wait_time, action_always, action_paused, action_started, action_stopped):
        self.logger = logger
        self._wait_time = wait_time
        self.action_when_paused = action_paused
        self.action_when_started = action_started
        self.action_when_stopped = action_stopped
        self.action_always = action_always
        self.short_press_notified = False
        self.long_press_notified = False
        self.state = PAUSED

    def notify_short_press(self):
        self.short_press_notified = True

    def acknowledge_short_press(self):
        self.short_press_notified = False

    def notify_long_press(self):
        self.long_press_notified = True

    def acknowledge_long_press(self):
        self.long_press_notified = False

    def transition_to_stopped(self):
        self.logger.deactivate()
        if not self.logger.active:
            self.acknowledge_long_press()
            if not utoken.exists():
                utoken.create()
            self.state = STOPPED

    def transition_to_paused(self):
        self.logger.deactivate()
        if not self.logger.active:
            self.acknowledge_short_press()
            self.state = PAUSED

    def transition_to_started(self):
        self.logger.activate()
        if self.logger.active:
            self.acknowledge_short_press()
            self.state = STARTED

    async def update_state(self):
        while True:
            self.action_always()
            if self.state == PAUSED:
                self.action_when_paused()
                if self.long_press_notified:
                    self.transition_to_stopped()
                elif self.short_press_notified:
                    self.transition_to_started()
            elif self.state == STARTED:
                self.action_when_started()
                if self.long_press_notified:
                    self.transition_to_stopped()
                elif self.short_press_notified:
                    self.transition_to_paused()
            elif self.state == STOPPED:
                self.action_when_stopped()
            else:
                print("Error.")
            await asyncio.sleep_ms(self._wait_time)
