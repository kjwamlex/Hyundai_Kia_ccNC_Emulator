#!/usr/bin/python3
"""Bound verbose OEM DLT output in guest tmpfs while retaining lifecycle state."""
from collections import deque
from pathlib import Path
import re
import sys
import time

recent = deque(maxlen=4096)
states = {}
path = Path(sys.argv[1])
lifecycles = path.parent / 'lifecycle'
lifecycles.mkdir(parents=True, exist_ok=True)
with path.open('wb', buffering=0) as stream:
    for line in sys.stdin.buffer:
        recent.append(line)
        state = re.search(rb'CHANGED : ([a-z0-9_-]+) - state:', line)
        if state:
            states[state[1]] = line
            # A separate small atomic record keeps launch readiness independent
            # of DLT truncation and very fast log growth during app startup.
            record = lifecycles / state[1].decode()
            temporary = record.with_suffix('.tmp')
            temporary.write_bytes(str(time.monotonic_ns()).encode() + b'\n' + line)
            temporary.replace(record)
        if b'device is added (statusbarhmi device)' in line:
            states[b'input-ready'] = line
        if stream.tell() > 32 * 1024 * 1024:
            stream.seek(0)
            stream.truncate()
            stream.write(b'CCNC_DLT_ROTATED: latest lifecycle states and recent output retained\n')
            for saved in states.values():
                stream.write(saved)
            for saved in list(recent)[:-1]:
                stream.write(saved)
        stream.write(line)
