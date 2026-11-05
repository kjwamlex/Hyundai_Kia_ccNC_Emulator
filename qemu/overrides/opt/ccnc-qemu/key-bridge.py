#!/usr/bin/env python3
"""Lab navigation keys, replacing the unavailable physical head-unit keys."""
import glob
import os
import select
import struct
import subprocess

KEYS = {59: 'home', 60: 'media', 61: 'phone', 62: 'audio', 63: 'settings',
        64: 'welcome', 65: 'goodbye', 66: 'tone', 67: 'engineering'}
EVENT = struct.Struct('llHHi')
devices = []
for path in glob.glob('/sys/class/input/event*/device/name'):
    if 'QEMU' in open(path).read() and 'Keyboard' in open(path).read():
        event = path.split('/')[4]
        devices.append(os.open('/dev/input/' + event, os.O_RDONLY | os.O_NONBLOCK))
if not devices:
    raise SystemExit('CCNC_KEY_ERROR: no QEMU keyboard')
print('CCNC_KEYS_READY: F1 Home, F2 Media, F3 Phone, F4 Audio, F5 Settings, F6 welcome, F7 goodbye, F8 test tone, F9 engineering', flush=True)
while True:
    ready, _, _ = select.select(devices, [], [])
    for device in ready:
        data = os.read(device, EVENT.size * 64)
        for offset in range(0, len(data), EVENT.size):
            _, _, kind, code, value = EVENT.unpack_from(data, offset)
            if kind == 1 and value == 1 and code in KEYS:
                subprocess.Popen(['/opt/ccnc-qemu/open-app.sh', KEYS[code]], close_fds=True)
