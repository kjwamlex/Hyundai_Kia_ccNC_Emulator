#!/usr/bin/env python3
"""Verify OEM playback, silence on mute, and resumed PCM in QEMU's capture."""
import array
import json
import math
import sys
import wave
from pathlib import Path

path = Path(sys.argv[1])
phases = json.loads(path.with_suffix(".phases.json").read_text())
with wave.open(str(path), "rb") as recording:
    assert recording.getsampwidth() == 2
    rate, channels = recording.getframerate(), recording.getnchannels()
raw = path.read_bytes()
frame_size = channels * 2
levels = {}
for name in ("high", "mute", "resume"):
    if name == "mute" and phases["mute_end"] == phases["mute_start"]:
        # OEM regular mute suspends its PCM writer; QEMU emits no frames.
        levels[name] = 0.0
        continue
    # Exclude QEMU's buffered write boundary at each marker.
    start = phases[name + "_start"] + int(rate * .3) * frame_size
    end = phases[name + "_end"] - int(rate * .3) * frame_size
    start -= (start - 44) % frame_size
    end -= (end - 44) % frame_size
    assert end - start > rate * frame_size, f"Phase {name} is too short"
    samples = array.array("h", raw[start:end])
    if sys.byteorder != "little":
        samples.byteswap()
    levels[name] = math.sqrt(sum(x*x for x in samples) / len(samples))
assert levels["high"] > 30, f"OEM playback is silent/too quiet: {levels}"
assert levels["mute"] < 1, f"Mute left an audible signal: {levels}"
assert levels["resume"] > 30, f"OEM playback failed to resume: {levels}"
assert channels == 2, "Expected stereo output"
# The first Settings click requests a HAL beep before OEM media starts.
samples = array.array("h", raw[44:44 + rate * frame_size])
if sys.byteorder != "little":
    samples.byteswap()
mono = samples[::channels]
first = next(i for i, value in enumerate(mono) if abs(value) > 3)
beep = mono[first:first + int(rate * .035)]
def power(frequency):
    return abs(sum(value * complex(math.cos(2*math.pi*frequency*i/rate),
                                   math.sin(2*math.pi*frequency*i/rate))
                   for i, value in enumerate(beep))) ** 2
assert power(1000) > 100 * max(power(440), power(1600), 1), "HAL beep missing from output"
print(f"CCNC_OEM_PCM_OK: {rate} Hz stereo; RMS " + ", ".join(f"{k}={v:.2f}" for k,v in levels.items()) + "; HAL beep verified")
