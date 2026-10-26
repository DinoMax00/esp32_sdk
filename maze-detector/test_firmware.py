"""Run the actual MicroPython main loop against a timed contact waveform."""

import contextlib
import io
import json
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class EndSimulation(Exception):
    pass


def simulate(waveform, duration):
    clock = SimpleNamespace(now=0)

    class Pin:
        IN = 0
        IRQ_FALLING = 1

        def __init__(self, number, mode, pull=None):
            assert number == 3 and mode == self.IN and pull is None
            self.handler = None

        def value(self):
            return next(value for start, value in reversed(waveform) if start <= clock.now)

        def irq(self, trigger, handler):
            self.handler = handler

    pin = Pin(3, Pin.IN)

    def sleep_ms(ms):
        before = pin.value()
        clock.now += ms
        after = pin.value()
        if before == 1 and after == 0 and pin.handler:
            pin.handler(pin)
        if clock.now >= duration:
            raise EndSimulation()

    timer = SimpleNamespace(ticks_ms=lambda: clock.now,
                            ticks_diff=lambda a, b: a - b, sleep_ms=sleep_ms)
    class MachinePin:
        IN = Pin.IN
        IRQ_FALLING = Pin.IRQ_FALLING

        def __new__(cls, number, mode, pull=None):
            assert number == 3 and mode == Pin.IN and pull is None
            return pin

    output = io.StringIO()
    with patch.dict('sys.modules', {'machine': SimpleNamespace(Pin=MachinePin), 'time': timer}):
        with contextlib.redirect_stdout(output):
            try:
                runpy.run_path(str(Path(__file__).with_name('main.py')))
            except EndSimulation:
                pass
    return [json.loads(line) for line in output.getvalue().splitlines()]


class FirmwareDebounceTest(unittest.TestCase):
    def test_brief_break_does_not_report_clear_or_count_twice(self):
        frames = simulate([(0, 1), (10, 0), (990, 1), (1010, 0), (1030, 1)], 1250)
        touch = [x for x in frames if x['event'] == 'contact']
        self.assertEqual(len(touch), 1)
        self.assertEqual(touch[0]['uptime_ms'], 10)
        heartbeat = next(x for x in frames if x['event'] == 'heartbeat')
        self.assertEqual((heartbeat['raw'], heartbeat['state']), (1, 'TOUCH'))
        released = [x for x in frames if x['event'] == 'released']
        self.assertEqual([x['uptime_ms'] for x in released], [1230])
        self.assertEqual(released[0]['state'], 'CLEAR')

    def test_new_touch_after_confirmed_release_is_immediate(self):
        frames = simulate([(0, 1), (10, 0), (20, 1), (300, 0)], 350)
        self.assertEqual([x['uptime_ms'] for x in frames if x['event'] == 'contact'], [10, 300])
        self.assertEqual([x['uptime_ms'] for x in frames if x['event'] == 'released'], [220])


if __name__ == '__main__':
    unittest.main()
