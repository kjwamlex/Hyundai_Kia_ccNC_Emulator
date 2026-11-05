#!/usr/bin/env python3
"""Replay OEM welcome videos through the lab framebuffer, without NVIDIA sinks."""
import fcntl
import json
import mmap
import os
from pathlib import Path
import selectors
import signal
import struct
import subprocess
import sys
import time

RUNTIME = Path('/run/ccnc-qemu')
CUSTOM = Path('/ccos/data/qemu')
FPS = 25


def interrupted(signum, frame):
    raise InterruptedError('animation interrupted')


def play(kind):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME / 'animation.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('CCNC_ANIMATION_BUSY', flush=True)
            return
        video = CUSTOM / (kind + '.264')
        if not video.is_file():
            # variantservice generates this file from the active vehicle coding.
            variants = Path('/tmp/ccos/sw_feature.json')
            brand = json.loads(variants.read_text())['SW.CAR_BRAND'].lower()
            if brand not in ('hyundai', 'kia', 'genesis'):
                raise RuntimeError('unsupported animation brand: ' + brand)
            video = Path('/ccos/services/welcomeaniservice/lhd') / (kind + '_' + brand + '_avnt.264')
        if not video.is_file():
            raise RuntimeError('animation file missing: ' + str(video))
        print('CCNC_ANIMATION_SOURCE: ' + str(video), flush=True)
        weston = int((RUNTIME / 'weston.pid').read_text())
        if Path('/proc/%d/comm' % weston).read_text().strip() != 'weston':
            raise RuntimeError('Weston PID is no longer valid')
        sound = CUSTOM / (kind + '.wav')
        decoder = audio = screen = None
        stopped = False
        saved = None
        try:
            with open('/dev/fb0', 'r+b', buffering=0) as framebuffer:
                info = bytearray(160)
                fcntl.ioctl(framebuffer, 0x4600, info)  # FBIOGET_VSCREENINFO
                fields = struct.unpack_from('=40I', info)
                width, height, _, virtual_height, xoffset, yoffset, bpp = fields[:7]
                if bpp != 32 or fields[8:16] != (16, 8, 0, 8, 8, 0, 0, 8):
                    raise RuntimeError('animation requires a 32-bit BGR framebuffer')
                stride = int(Path('/sys/class/graphics/fb0/stride').read_text())
                screen = mmap.mmap(framebuffer.fileno(), stride * virtual_height)
                os.kill(weston, signal.SIGSTOP)
                stopped = True
                for _ in range(100):
                    if '\nState:\tT' in Path('/proc/%d/status' % weston).read_text():
                        break
                    time.sleep(0.01)
                else:
                    raise RuntimeError('Weston did not pause')
                saved = screen[:]
                decoder = subprocess.Popen([
                    'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                    '-i', str(video), '-an', '-t', '15', '-vf',
                    'fps=%d,scale=%d:%d:force_original_aspect_ratio=decrease,'
                    'pad=%d:%d:(ow-iw)/2:(oh-ih)/2' % (FPS, width, height, width, height),
                    '-c:v', 'bmp', '-pix_fmt', 'bgra', '-f', 'image2pipe', 'pipe:1'],
                    stdout=subprocess.PIPE, bufsize=0)
                deadline = time.monotonic() + 30
                with selectors.DefaultSelector() as selector:
                    selector.register(decoder.stdout, selectors.EVENT_READ)

                    def read_exact(size):
                        data = bytearray()
                        while len(data) < size:
                            remaining = deadline - time.monotonic()
                            if remaining <= 0 or not selector.select(remaining):
                                raise RuntimeError('animation decoder timed out')
                            chunk = os.read(decoder.stdout.fileno(), size - len(data))
                            if not chunk:
                                if not data:
                                    return None
                                raise RuntimeError('truncated animation frame')
                            data.extend(chunk)
                        return data

                    frames = 0
                    started = None
                    print('CCNC_ANIMATION_STARTED: %s sound=%s' %
                          (kind, str(sound) if sound.is_file() else 'none'), flush=True)
                    while True:
                        header = read_exact(14)
                        if header is None:
                            break
                        size, offset = struct.unpack_from('<I4xI', header, 2)
                        if header[:2] != b'BM' or not 54 <= size <= width * height * 4 + 4096:
                            raise RuntimeError('invalid animation frame')
                        body = read_exact(size - 14)
                        if body is None:
                            raise RuntimeError('missing animation pixels')
                        w, h, planes, depth = struct.unpack_from('<iiHH', body, 4)
                        if (w, h, planes, depth) != (width, height, 1, 32):
                            raise RuntimeError('unexpected animation dimensions or pixel format')
                        pixels = memoryview(body)[offset - 14:]
                        if len(pixels) != width * height * 4:
                            raise RuntimeError('unexpected animation frame size')
                        # BMP is bottom-up. The vendor BMP encoder crashes on the
                        # negative row stride produced by FFmpeg's vflip filter.
                        pixels = b''.join(pixels[row * width * 4:(row + 1) * width * 4]
                                          for row in reversed(range(height)))
                        if started is None:
                            started = time.monotonic()
                            if sound.is_file():
                                audio = subprocess.Popen(['aplay', '-q', '-D', 'default', str(sound)])
                        time.sleep(max(0, started + frames / FPS - time.monotonic()))
                        start = yoffset * stride + xoffset * 4
                        if stride == width * 4 and not xoffset:
                            screen[start:start + len(pixels)] = pixels
                        else:
                            for row in range(height):
                                screen[start + row * stride:start + row * stride + width * 4] = \
                                    pixels[row * width * 4:(row + 1) * width * 4]
                        frames += 1
                        if frames == 25:
                            print('CCNC_ANIMATION_VISIBLE: ' + kind, flush=True)
                    status = decoder.wait(timeout=3)
                    if status or not frames:
                        raise RuntimeError('animation decode failed: status=%d frames=%d' % (status, frames))
        finally:
            for process in (decoder, audio):
                if process is not None:
                    if process.poll() is None:
                        process.kill()
                    process.wait()
                    if process.stdout is not None:
                        process.stdout.close()
            if screen is not None:
                if saved is not None:
                    screen[:] = saved
                screen.close()
            if stopped:
                os.kill(weston, signal.SIGCONT)
                subprocess.run(['/opt/ccnc-qemu/open-app.sh', 'home'], timeout=7, check=True)
        print('CCNC_ANIMATION_DONE: %s frames=%d' % (kind, frames), flush=True)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    if len(sys.argv) != 2 or sys.argv[1] not in ('welcome', 'goodbye'):
        raise SystemExit('Usage: play-animation.py welcome|goodbye')
    try:
        play(sys.argv[1])
    except Exception as error:
        print('CCNC_ANIMATION_ERROR: ' + str(error), flush=True)
        raise SystemExit(1)
