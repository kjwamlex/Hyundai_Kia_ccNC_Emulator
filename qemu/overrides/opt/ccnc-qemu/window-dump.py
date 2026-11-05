#!/usr/bin/python3
"""Read compositor window state through the OEM Wayland dumper protocol."""
import array
import json
import os
import socket
import struct
import sys

s = socket.socket(socket.AF_UNIX)
s.settimeout(4)
s.connect('/run/user/0/wayland-system')

def send(obj, op, body=b''):
    s.sendall(struct.pack('<II', obj, ((8 + len(body)) << 16) | op) + body)

def string(value):
    value = value.encode() + b'\0'
    return struct.pack('<I', len(value)) + value + bytes(-len(value) % 4)

pending = b''
fds = []
def receive():
    global pending
    while len(pending) < 8 or len(pending) < struct.unpack_from('<I', pending, 4)[0] >> 16:
        data, anc, flags, addr = s.recvmsg(65536, socket.CMSG_SPACE(16))
        if not data:
            raise RuntimeError('Disconnected')
        pending += data
        for level, kind, val in anc:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                a = array.array('i'); a.frombytes(val); fds.extend(a)
    obj, word = struct.unpack_from('<II', pending)
    n = word >> 16
    body, pending = pending[8:n], pending[n:]
    return obj, word & 65535, body

send(1, 1, struct.pack('<I', 2))
send(1, 0, struct.pack('<I', 3))
dumper = None
while True:
    obj, op, body = receive()
    if obj == 2 and op == 0:
        name, n = struct.unpack_from('<II', body)
        if body[8:8+n-1] == b'dumper':
            dumper = name
    if obj == 3:
        break
if dumper is None:
    raise RuntimeError('OEM compositor does not expose the dumper protocol')
send(2, 0, struct.pack('<I', dumper) + string('dumper') + struct.pack('<II', 1, 4))
send(4, 1, struct.pack('<I', 5))
while True:
    obj, op, body = receive()
    if obj == 1 and op == 0:
        raise RuntimeError(repr(body))
    if obj == 5:
        break
with os.fdopen(fds.pop(0)) as f:
    f.seek(0)
    state = json.load(f)
s.close()
if len(sys.argv) == 3 and sys.argv[1] == '--expect-update':
    expected = {'visible': True, 'hidden': False}[sys.argv[2]]
    popups = [value for key, value in state[0]['windows']
              if key['name'].startswith('UPDATE.POPUP.')]
    visible = [p for p in popups if p['visibility'] and p['displayed']]
    assert bool(visible) == expected, 'Unexpected update popup visibility: %s' % popups
    if expected:
        assert any(p['focus'] and p['opacity'] == 1.0 and p.get('surfaceId') for p in visible), visible
    print('CCNC_UPDATE_POPUP_' + sys.argv[2].upper())
elif len(sys.argv) == 4 and sys.argv[1] == '--expect-window':
    name, visibility = sys.argv[2:]
    expected = {'visible': True, 'hidden': False}[visibility]
    windows = [value for key, value in state[0]['windows'] if key['name'] == name]
    assert windows, 'Window not registered: ' + name
    shown = [w for w in windows if w['visibility'] and w['displayed'] and w['opacity'] == 1.0]
    assert bool(shown) == expected, 'Unexpected window visibility: %s' % windows
    if expected:
        assert any(w.get('surfaceId') for w in shown), shown
    print('CCNC_WINDOW_OK: ' + name + ' ' + visibility)
else:
    print(json.dumps(state, indent=2))
