"""Exercise the real serial-to-HTTP path using a pseudo-terminal, not the board."""

import http.client
import json
import os
import pty
import threading
import unittest
from http.server import ThreadingHTTPServer

from web_server import Detector, make_handler


class SerialWebIntegrationTest(unittest.TestCase):
    def test_live_contact_release_and_disconnect(self):
        master, slave = pty.openpty()
        detector = Detector(os.ttyname(slave))
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(detector))
        reader = threading.Thread(target=detector.run, daemon=True)
        http_worker = threading.Thread(target=server.serve_forever, daemon=True)
        reader.start()
        http_worker.start()
        port = server.server_port

        def send(raw):
            packet = json.dumps({'pin': 'D1/GPIO3', 'raw': raw,
                                 'event': 'heartbeat', 'contacts': 0}).encode() + b'\n'
            # Split a packet to exercise serial framing across read boundaries.
            os.write(master, packet[:15])
            os.write(master, packet[15:])

        def wait_for(predicate):
            with detector.condition:
                self.assertTrue(detector.condition.wait_for(predicate, timeout=3))

        try:
            # Wait for the worker to finish configuring the terminal.
            for _ in range(20):
                send(1)
                with detector.condition:
                    if detector.condition.wait_for(lambda: detector.connected, timeout=0.1):
                        break
            self.assertTrue(detector.connected)
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            conn.request('GET', '/api/status')
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())['reading']['raw'], 1)
            conn.close()

            stream = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            stream.request('GET', '/events')
            events = stream.getresponse()
            self.assertIn('text/event-stream', events.getheader('Content-Type'))

            def next_event(predicate):
                while True:
                    line = events.readline()
                    self.assertTrue(line)
                    if line.startswith(b'data: '):
                        data = json.loads(line[6:])
                        if predicate(data):
                            return data

            next_event(lambda data: data['connected'] and data['reading']['raw'] == 1)
            send(0)
            wait_for(lambda: detector.reading['raw'] == 0)
            next_event(lambda data: data['connected'] and data['reading']['raw'] == 0)
            send(1)
            wait_for(lambda: detector.reading['raw'] == 1)
            next_event(lambda data: data['connected'] and data['reading']['raw'] == 1)
            os.close(master)
            master = None
            wait_for(lambda: not detector.connected)
            next_event(lambda data: not data['connected'])
            stream.close()

            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            conn.request('GET', '/')
            response = conn.getresponse()
            page = response.read().decode()
            self.assertEqual(response.status, 200)
            self.assertIn('contact-flash 1s', page)
            self.assertNotIn('重新开始', page)
            conn.close()
        finally:
            detector.stop.set()
            with detector.condition:
                detector.condition.notify_all()
            server.shutdown()
            server.server_close()
            reader.join(timeout=2)
            os.close(slave)
            if master is not None:
                os.close(master)


if __name__ == '__main__':
    unittest.main()
