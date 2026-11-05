#!/usr/bin/env python3
"""Check local prerequisites and build the ccNC QEMU environment from source."""
import argparse
from pathlib import Path
import platform
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
FIRMWARE = (
    '1_gos1-fs_7_ext4.img',
    '1_4_tegra_dtb_zerosign.dtb',
    '1_5_kernel_zerosign.img',
    '2_4_tegra_dtb_zerosign.dtb',
    '2_5_kernel_zerosign.img',
    '2_6_ramdisk_zerosign.img',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check only; do not download or build')
    args = parser.parse_args()
    problems = []
    print('Host: %s %s' % (platform.system(), platform.machine()))
    if sys.version_info < (3, 12):
        problems.append('Python 3.12 or newer is required')
    for command in ('qemu-system-aarch64', 'qemu-img', 'lz4', 'dtc'):
        found = shutil.which(command)
        print('%s: %s' % (command, found or 'MISSING'))
        if not found:
            problems.append('Missing host tool: ' + command)
    homebrew_clang = Path('/opt/homebrew/opt/llvm/bin/clang')
    clang = str(homebrew_clang) if homebrew_clang.is_file() else shutil.which('clang')
    lld = shutil.which('ld.lld')
    if not lld and clang:
        candidate = Path(clang).resolve().parent / 'ld.lld'
        if candidate.is_file():
            lld = str(candidate)
    print('clang: %s' % (clang or 'MISSING'))
    print('ld.lld: %s' % (lld or 'MISSING'))
    if not clang or not lld:
        problems.append('Install LLVM and lld (on macOS: brew install llvm lld)')
    for name in FIRMWARE:
        path = HERE.parent / 'system' / name
        present = path.is_file() and path.stat().st_size > 0
        print('system/%s: %s' % (name, 'present' if present else 'MISSING'))
        if not present:
            problems.append('Supply your own prepared firmware: system/' + name)
    if problems:
        raise SystemExit('\nPrerequisites not satisfied:\n- ' + '\n- '.join(problems))
    print('Prerequisites satisfied.', flush=True)
    if args.check:
        return
    for script in ('prepare.py', 'compat/build.py', 'compat/prepare-mesa.py', 'prepare-audio.py'):
        print('\nRunning ' + script, flush=True)
        subprocess.run([sys.executable, str(HERE / script)], cwd=HERE.parent, check=True)
    print('\nReady: python3 qemu/run.py --gui ccnc --state')


if __name__ == '__main__':
    main()
