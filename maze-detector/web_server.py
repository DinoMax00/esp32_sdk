"""Local, read-only USB serial bridge and full-screen maze visualization.

Run: python3 maze-detector/web_server.py
"""

import argparse
import glob
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import select
import termios
import threading
import time

WEB_ROOT = Path(__file__).resolve().parent / "web"
STALE_SECONDS = 3.5


class Detector:
    def __init__(self, port=None):
        self.port = port
        self.condition = threading.Condition()
        self.sequence = 0
        self.connected = False
        self.reading = None
        self.last_received = 0
        self.stop = threading.Event()

    def snapshot(self):
        # Callers hold the condition, or use the lock below.
        return {"connected": self.connected, "reading": self.reading}

    def update(self, reading=None, connected=False):
        with self.condition:
            self.connected = connected
            if reading is not None:
                self.reading = reading
                self.last_received = time.monotonic()
            self.sequence += 1
            self.condition.notify_all()

    def run(self):
        while not self.stop.is_set():
            ports = [self.port] if self.port else sorted(glob.glob('/dev/cu.usbmodem*'))
            if not ports:
                self.stop.wait(1)
                continue
            fd = None
            original = None
            try:
                fd = os.open(ports[0], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
                original = termios.tcgetattr(fd)
                config = original.copy()
                config[6] = original[6].copy()
                config[0] = config[1] = config[3] = 0
                config[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
                config[4] = config[5] = termios.B115200
                config[6][termios.VMIN] = config[6][termios.VTIME] = 0
                # Do not toggle DTR/RTS: opening a serial library can reset C3.
                termios.tcsetattr(fd, termios.TCSANOW, config)
                buffer = bytearray()
                opened = time.monotonic()
                while not self.stop.is_set():
                    ready, _, _ = select.select([fd], [], [], 0.2)
                    if ready:
                        try:
                            data = os.read(fd, 4096)
                        except BlockingIOError:
                            data = None
                        if data == b'':
                            raise OSError('Serial device disconnected')
                        if data:
                            buffer.extend(data)
                        if len(buffer) > 65536:
                            buffer.clear()
                        while b'\n' in buffer:
                            raw, _, rest = buffer.partition(b'\n')
                            buffer = bytearray(rest)
                            try:
                                reading = json.loads(raw)
                            except (ValueError, UnicodeError):
                                continue
                            if (isinstance(reading, dict)
                                and reading.get('pin') == 'D1/GPIO3'
                                and type(reading.get('raw')) is int
                                and reading['raw'] in (0, 1)):
                                self.update(reading=reading, connected=True)
                    if time.monotonic() - max(opened, self.last_received) > STALE_SECONDS:
                        raise OSError('No detector heartbeat')
            except (OSError, termios.error):
                if self.connected:
                    self.update(connected=False)
            finally:
                if fd is not None:
                    try:
                        if original is not None:
                            termios.tcsetattr(fd, termios.TCSANOW, original)
                    except (OSError, termios.error):
                        pass
                    os.close(fd)
            self.stop.wait(1)


def make_handler(detector):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def do_GET(self):
            route = self.path.split('?', 1)[0]
            if route == '/events':
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.end_headers()
                self.connection.settimeout(5)
                sequence = -1
                try:
                    while not detector.stop.is_set():
                        with detector.condition:
                            detector.condition.wait_for(
                                lambda: detector.sequence != sequence or detector.stop.is_set(),
                                timeout=1,
                            )
                            sequence = detector.sequence
                            payload = json.dumps(detector.snapshot())
                        self.wfile.write(('data: ' + payload + '\n\n').encode())
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
                    pass
                self.close_connection = True
                return
            if route == '/api/status':
                with detector.condition:
                    body = json.dumps(detector.snapshot()).encode()
                self.respond(body, 'application/json; charset=utf-8')
                return
            files = {
                '/': ('index.html', 'text/html; charset=utf-8'),
                '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                '/state.mjs': ('state.mjs', 'text/javascript; charset=utf-8'),
            }
            if route not in files:
                self.send_error(404)
                return
            name, mime = files[route]
            self.respond((WEB_ROOT / name).read_bytes(), mime)

        def respond(self, body, content_type):
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--serial', default=None, help='Defaults to /dev/cu.usbmodem*')
    args = parser.parse_args()
    detector = Detector(args.serial)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(detector))
    worker = threading.Thread(target=detector.run, daemon=True)
    worker.start()
    print('铁丝迷宫：http://127.0.0.1:' + str(args.port), flush=True)
    print('接触：红色闪烁；分开：绿色。按 Ctrl+C 停止。', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        detector.stop.set()
        with detector.condition:
            detector.condition.notify_all()
        server.server_close()
        worker.join(timeout=2)


if __name__ == '__main__':
    main()
