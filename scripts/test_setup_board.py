"""Installer safety checks with temporary files; never access a real device."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import setup_board


class InstallerTest(unittest.TestCase):
    def test_verified_cache_needs_no_download(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'firmware').mkdir()
            target = root / 'firmware' / setup_board.FIRMWARE_NAME
            target.write_bytes(b'test firmware')
            checksum = hashlib.sha256(target.read_bytes()).hexdigest()
            with patch.object(setup_board, 'PROJECT', root), \
                 patch.object(setup_board, 'FIRMWARE_SHA256', checksum), \
                 patch.object(setup_board.urllib.request, 'urlopen') as request:
                self.assertEqual(setup_board.download_firmware(), target)
                request.assert_not_called()

    def test_incomplete_backup_stops_before_flash_or_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calls = []

            def run(module, *args, **kwargs):
                calls.append((module, args))
                if 'read_flash' in args:
                    Path(args[-1]).write_bytes(b'incomplete')

            with patch.object(setup_board, 'PROJECT', root), \
                 patch.object(setup_board, 'download_firmware', return_value=root / 'runtime.bin'), \
                 patch.object(setup_board, 'run', side_effect=run), \
                 patch('sys.argv', ['setup_board.py', '--port', '/dev/fake', '--install-runtime']):
                with self.assertRaisesRegex(RuntimeError, '备份不完整'):
                    setup_board.main()
            self.assertEqual(len(calls), 1)
            self.assertIn('read_flash', calls[0][1])

    def test_upload_hash_mismatch_prevents_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'main.py').write_text('print("test")\n')
            with patch.object(setup_board, 'PROJECT', root), \
                 patch.object(setup_board, 'run', side_effect=[None, 'wrong hash']) as run, \
                 patch('sys.argv', ['setup_board.py', '--port', '/dev/fake']):
                with self.assertRaisesRegex(RuntimeError, '校验失败'):
                    setup_board.main()
                self.assertEqual(run.call_count, 2)
                self.assertNotIn('reset', run.call_args.args)


if __name__ == '__main__':
    unittest.main()
