#!/usr/bin/env python3
"""Verify that the actual QEMU recording contains the guest's 440 Hz test tone."""
import array
import math
import sys
import wave
from pathlib import Path


def verify(path):
    with wave.open(str(path), "rb") as recording:
        assert recording.getsampwidth() == 2, "Expected 16-bit PCM"
        rate = recording.getframerate()
        channels = recording.getnchannels()
        samples = array.array("h", recording.readframes(recording.getnframes()))
    if sys.byteorder != "little":
        samples.byteswap()
    signal = list(samples[::channels])
    active = [i for i, value in enumerate(signal) if abs(value) > 30]
    assert len(active) > rate // 4, "Audio capture is silent or too short"
    signal = signal[active[0]:active[0] + rate // 2]
    rms = math.sqrt(sum(value * value for value in signal) / len(signal))

    def power(frequency):
        real = sum(value * math.cos(2 * math.pi * frequency * i / rate) for i, value in enumerate(signal))
        imag = sum(value * math.sin(2 * math.pi * frequency * i / rate) for i, value in enumerate(signal))
        return real * real + imag * imag

    assert rms > 50, f"Output too quiet: RMS {rms:.1f}"
    assert power(440) > 100 * max(power(1000), 1), "Captured signal does not contain the expected tone"
    print(f"CCNC_AUDIO_CAPTURE_OK: {rate} Hz, {channels} channels, RMS {rms:.1f}, 440 Hz tone verified")


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
