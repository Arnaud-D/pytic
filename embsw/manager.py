import uasyncio as asyncio
import utoken


class State:
    PAUSED = 0
    STARTED = 1
    STOPPED = 2


class Event:
    EVENT1 = 0
    EVENT2 = 1


class Manager:
    """Manage the state of the device."""
    def __init__(self, logger, wait_time, on_init, on_pause, on_start, on_stop):
        self.logger = logger
        self.wait_time = wait_time
        self.on_pause = on_pause
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_init = on_init
        self.event1_notified = False
        self.event2_notified = False
        self.state = State.PAUSED

    def notify(self, event):
        if event == Event.EVENT1:
            self.event1_notified = True
        elif event == Event.EVENT2:
            self.event2_notified = True
        else:
            raise ValueError

    def acknowledge(self, event):
        if event == Event.EVENT1:
            self.event1_notified = False
        elif event == Event.EVENT2:
            self.event2_notified = False
        else:
            raise ValueError

    def transition(self, dest_state):
        # Transition to STOPPED
        if (self.state == State.PAUSED or self.state == State.STARTED) and dest_state == State.STOPPED:
            self.logger.deactivate()
            if not self.logger.active:
                self.acknowledge(Event.EVENT2)
                if not utoken.exists():
                    utoken.create()
                self.on_stop()
                self.state = State.STOPPED
        # Transition to PAUSED
        elif self.state == State.STARTED and dest_state == State.PAUSED:
            self.logger.deactivate()
            if not self.logger.active:
                self.acknowledge(Event.EVENT1)
                self.on_pause()
                self.state = State.PAUSED
        # Transition to STARTED
        elif self.state == State.PAUSED and dest_state == State.STARTED:
            self.logger.activate()
            if self.logger.active:
                self.acknowledge(Event.EVENT1)
                self.on_start()
                self.state = State.STARTED

    async def execute(self):
        self.on_init()
        while True:
            if self.state == State.PAUSED:
                if self.event2_notified:
                    self.transition(State.STOPPED)
                elif self.event1_notified:
                    self.transition(State.STARTED)
            elif self.state == State.STARTED:
                if self.event2_notified:
                    self.transition(State.STOPPED)
                elif self.event1_notified:
                    self.transition(State.PAUSED)
            elif self.state == State.STOPPED:
                pass
            else:
                raise ValueError
            await asyncio.sleep_ms(self.wait_time)
