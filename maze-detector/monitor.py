"""Read detector output without sending commands or resetting the ESP32."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import select
import termios
import time

parser = argparse.ArgumentParser()
parser.add_argument("--port", default="/dev/cu.usbmodem1101")
parser.add_argument("--seconds", type=float, default=15)
args = parser.parse_args()

log_dir = Path(__file__).resolve().parent / "logs"
log_dir.mkdir(exist_ok=True)
log_path = log_dir / (datetime.now().strftime("serial-%Y%m%d-%H%M%S") + ".jsonl")

# Avoid serial-library DTR/RTS ioctls: those reset this board on reconnect.
fd = os.open(args.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
original = termios.tcgetattr(fd)
settings = original.copy()
settings[6] = original[6].copy()
settings[0] = 0
settings[1] = 0
settings[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
settings[3] = 0
settings[4] = settings[5] = termios.B115200
settings[6][termios.VMIN] = 0
settings[6][termios.VTIME] = 0
termios.tcsetattr(fd, termios.TCSANOW, settings)
buffer = bytearray()


def readline():
    end = time.monotonic() + 0.5
    while True:
        if b"\n" in buffer:
            index = buffer.index(b"\n") + 1
            line = bytes(buffer[:index])
            del buffer[:index]
            return line
        remaining = end - time.monotonic()
        if remaining <= 0:
            return b""
        ready, _, _ = select.select([fd], [], [], remaining)
        if ready:
            try:
                buffer.extend(os.read(fd, 4096))
            except BlockingIOError:
                pass

received = 0
states = set()
counts = []
deadline = time.monotonic() + args.seconds
print("Listening on", args.port, "for", args.seconds, "seconds", flush=True)
try:
    with log_path.open("w", encoding="utf-8") as log:
        while time.monotonic() < deadline:
            raw = readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            record = {"received_at": datetime.now().astimezone().isoformat(), "line": line}
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
            log.flush()
            print(line, flush=True)
            try:
                data = json.loads(line)
            except ValueError:
                continue
            if data.get("pin") != "D1/GPIO3":
                continue
            received += 1
            states.add(data.get("state"))
            counts.append(data.get("contacts", 0))
finally:
    try:
        termios.tcsetattr(fd, termios.TCSANOW, original)
    finally:
        os.close(fd)

print("SUMMARY", json.dumps({
    "messages": received,
    "states": sorted(states),
    "contact_count_first": counts[0] if counts else None,
    "contact_count_last": counts[-1] if counts else None,
    "log": str(log_path),
}), flush=True)
