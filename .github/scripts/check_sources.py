#!/usr/bin/env python3
"""Check syntax and allow only project sources, documentation and approved screenshots."""
import ast
import json
from pathlib import Path
import subprocess
import struct

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = {'artifacts', 'logs', 'state', '__pycache__', 'mesa',
             'usb-audit-archive', 'usb-audit-extracted'}
SUFFIXES = {'.py', '.sh', '.c', '.cpp', '.h', '.S', '.json', '.md', '.txt',
            '.rules', '.conf', '.command', '.yml', '.yaml'}
SCREENSHOTS = {'docs/screenshots/dashboard.png', 'docs/screenshots/software-info.png'}


def main():
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    failures = []
    total = 0
    count = 0
    for name in filter(None, tracked):
        path = Path(name)
        count += 1
        if path.parts[0] not in {'qemu', '.github', 'docs', '.gitignore', 'README.md', 'NOTICE.md'}:
            failures.append('Unexpected top-level path: ' + name)
        if FORBIDDEN.intersection(path.parts) or path.name == 'system_update.json':
            failures.append('Local firmware, runtime output, or fixture is tracked: ' + name)
        if name not in SCREENSHOTS and path.name != '.gitignore' and path.suffix not in SUFFIXES:
            failures.append('Unexpected source file type: ' + name)
        source = ROOT / path
        if source.is_symlink():
            failures.append('Source checkout contains a symlink: ' + name)
            continue
        data = source.read_bytes()
        total += len(data)
        if name in SCREENSHOTS:
            if (len(data) < 33 or len(data) > 3 * 1024 * 1024 or
                    data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR' or
                    not all(struct.unpack('>II', data[16:24]))):
                failures.append('Invalid or oversized documentation screenshot: ' + name)
            continue
        if len(data) > 1024 * 1024 or b'\0' in data:
            failures.append('Binary or oversized file: ' + name)
            continue
        try:
            text = data.decode('utf-8')
            if path.suffix == '.py':
                ast.parse(text, filename=name)
            elif path.suffix == '.json':
                json.loads(text)
            elif path.suffix in {'.sh', '.command'}:
                subprocess.run(['sh', '-n', str(source)], check=True, capture_output=True)
        except (UnicodeError, SyntaxError, ValueError, subprocess.CalledProcessError) as error:
            failures.append('%s: %s' % (name, error))
    if total > 5 * 1024 * 1024:
        failures.append('Source checkout exceeds the 5 MiB publication limit')
    if failures:
        raise SystemExit('\n'.join(failures))
    print('PASS: %d source/documentation files, %.1f KiB; syntax and firmware exclusions checked' %
          (count, total / 1024))


if __name__ == '__main__':
    main()
