"""XIAO ESP32C3 wire-loop contact detector: D1 = GPIO3.

Wiring: 3V3 -- 10k resistor -- GPIO3/red wire; black wire -- GND.
The ring touching the maze wire pulls GPIO3 LOW. External pull-up required.
"""

from machine import Pin
import time
import json

INPUT_GPIO = 3
RELEASE_DEBOUNCE_MS = 200
HEARTBEAT_MS = 1000

sensor = Pin(INPUT_GPIO, Pin.IN, pull=None)
armed = sensor.value() == 1
pending_touch = not armed
contacts = 0


def on_falling_edge(pin):
    # Capture short touches, but do not print or debounce inside the callback.
    global armed, pending_touch
    if armed:
        armed = False
        pending_touch = True


sensor.irq(trigger=Pin.IRQ_FALLING, handler=on_falling_edge)


def report(event):
    raw = sensor.value()
    print(json.dumps({
        "event": event,
        "pin": "D1/GPIO3",
        "raw": raw,
        # Keep TOUCH during brief breaks; raw remains available for diagnosis.
        "state": "CLEAR" if armed else "TOUCH",
        "contacts": contacts,
        "uptime_ms": time.ticks_ms(),
    }))


report("ready")
high_since = None
last_heartbeat = time.ticks_ms()

while True:
    now = time.ticks_ms()

    if pending_touch:
        pending_touch = False
        contacts += 1
        report("contact")

    if sensor.value() == 0:
        high_since = None
    elif not armed:
        if high_since is None:
            high_since = now
        elif time.ticks_diff(now, high_since) >= RELEASE_DEBOUNCE_MS:
            armed = True
            high_since = None
            report("released")

    if time.ticks_diff(now, last_heartbeat) >= HEARTBEAT_MS:
        report("heartbeat")
        last_heartbeat = now

    time.sleep_ms(1)
