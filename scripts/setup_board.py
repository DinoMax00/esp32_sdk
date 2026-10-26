"""Install / update the XIAO ESP32C3 maze detector from this checkout.

Default: upload main.py to an existing MicroPython installation.
--install-runtime: back up the original 4MiB flash, install MicroPython, upload.
--download-only: download and verify the official runtime without touching USB.
"""

import argparse
from datetime import datetime
import hashlib
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'maze-detector'
FIRMWARE_NAME = 'ESP32_GENERIC_C3-20260824-v1.29.0.bin'
FIRMWARE_URL = 'https://micropython.org/resources/firmware/' + FIRMWARE_NAME
FIRMWARE_SHA256 = 'bf72ed9eb88ad3a8f49d02c3d371f9ea34c90a8a303aeb9e324d8efd4a2a655a'
FLASH_BYTES = 4 * 1024 * 1024


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download_firmware():
    directory = PROJECT / 'firmware'
    directory.mkdir(exist_ok=True)
    target = directory / FIRMWARE_NAME
    if target.exists() and digest(target) == FIRMWARE_SHA256:
        print('固件缓存校验通过：', target, flush=True)
        return target
    partial = target.with_suffix('.bin.part')
    print('下载官方固件：', FIRMWARE_URL, flush=True)
    try:
        with urllib.request.urlopen(FIRMWARE_URL, timeout=120) as response:
            with partial.open('wb') as output:
                while True:
                    block = response.read(65536)
                    if not block:
                        break
                    output.write(block)
        actual = digest(partial)
        if actual != FIRMWARE_SHA256:
            raise RuntimeError('固件 SHA-256 不匹配，未执行烧录：' + actual)
        partial.replace(target)
    finally:
        if partial.exists():
            partial.unlink()
    print('固件 SHA-256 校验通过。', flush=True)
    return target


def run(module, *args, capture=False):
    command = [sys.executable, '-m', module, *map(str, args)]
    if capture:
        return subprocess.check_output(command, text=True).strip()
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', help='例如 /dev/cu.usbmodem1101')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--install-runtime', action='store_true')
    mode.add_argument('--download-only', action='store_true')
    args = parser.parse_args()

    if args.download_only:
        download_firmware()
        return
    if not args.port:
        parser.error('请用 --port 指定开发板串口；--download-only 不需要串口。')

    if args.install_runtime:
        runtime = download_firmware()
        backup_dir = PROJECT / 'backups'
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup = backup_dir / ('original-flash-' + stamp + '.bin')
        print('先备份原有固件：', backup, flush=True)
        run('esptool', '--chip', 'esp32c3', '--port', args.port, '--baud', '460800',
            'read_flash', '0', str(FLASH_BYTES), backup)
        if not backup.exists() or backup.stat().st_size != FLASH_BYTES:
            raise RuntimeError('原固件备份不完整，已停止，未执行烧录。')
        backup.with_suffix('.sha256').write_text(digest(backup) + '  ' + backup.name + '\n')
        run('esptool', '--chip', 'esp32c3', '--port', args.port, '--baud', '460800',
            'write_flash', '--erase-all', '0', runtime)

    source = PROJECT / 'main.py'
    run('mpremote', 'connect', args.port, 'fs', 'cp', source, ':main.py')
    actual = run('mpremote', 'connect', args.port, 'exec',
                 "import hashlib,binascii; print(binascii.hexlify(hashlib.sha256(open('main.py','rb').read()).digest()).decode())",
                 capture=True)
    if actual != digest(source):
        raise RuntimeError('上传的 main.py 校验失败，未执行复位。')
    run('mpremote', 'connect', args.port, 'reset')
    print('检测程序上传并校验成功。现在可以启动 maze-detector/web_server.py。', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print('安装失败：' + str(exc), file=sys.stderr)
        sys.exit(1)
