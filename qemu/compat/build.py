#!/usr/bin/env python3
"""Cross-compile the small AArch64 compatibility library with Homebrew LLVM."""
import shutil
import subprocess
import math
import struct
import wave
from pathlib import Path

here = Path(__file__).resolve().parent
clang = Path("/opt/homebrew/opt/llvm/bin/clang")
if not clang.exists():
    clang = shutil.which("clang")
out = here.parent / "overrides/opt/ccnc-qemu"
out.mkdir(parents=True, exist_ok=True)
with wave.open(str(out / "audio-check.wav"), "wb") as recording:
    recording.setparams((2, 2, 48000, 0, "NONE", "not compressed"))
    recording.writeframes(b"".join(struct.pack("<hh", value, value)
                          for value in (int(1800 * math.sin(2 * math.pi * 440 * i / 48000)) for i in range(48000))))
subprocess.run([str(clang), "--target=aarch64-linux-gnu", "-fuse-ld=lld", "-nostdlib",
                "-fPIC", "-shared", "-O2", "-Wall", "-Wextra", "-Werror",
                "-Wl,-soname,libashmem-qemu.so", "-Wl,-z,relro,-z,now",
                str(here / "ashmem-memfd.c"), "-o", str(out / "libashmem-qemu.so")], check=True)
print(out / "libashmem-qemu.so")
subprocess.run([str(clang), "--target=aarch64-linux-gnu", "-fuse-ld=lld", "-nostdlib",
                "-fPIC", "-shared", "-O2", "-Wall", "-Wextra", "-Werror",
                "-Wl,-soname,libaudio-platform-qemu.so", "-Wl,-z,relro,-z,now",
                str(here / "audio-platform.c"), "-o", str(out / "libaudio-platform-qemu.so")], check=True)
subprocess.run([str(clang), "--target=aarch64-linux-gnu", "-fuse-ld=lld", "-nostdlib",
                "-fPIC", "-shared", "-O2", "-Wall", "-Wextra", "-Werror",
                "-Wl,-soname,libsettings-platform-qemu.so", "-Wl,-z,relro,-z,now",
                str(here / "settings-platform.c"), "-o", str(out / "libsettings-platform-qemu.so")], check=True)
libc = here.parent / "artifacts/display/libc.so.6"
if libc.exists():
    subprocess.run([str(clang), "--target=aarch64-linux-gnu", "-fuse-ld=lld", "-nostdlib",
                    "-O2", "-fPIE", "-pie", "-Wl,-e,_start",
                    "-Wl,--dynamic-linker=/lib/ld-linux-aarch64.so.1", "-Wl,--allow-shlib-undefined",
                    str(here / "start.S"), str(here / "ashmem-test.c"),
                    str(here / "ashmem-memfd.c"), str(libc),
                    "-o", str(out / "ashmem-test")], check=True)

# Match the firmware's GNU C++11 string/list ABI using a pinned ARM64 sysroot.
sysroot = here.parent / "artifacts/sysroot"
if not (sysroot / "usr/include/c++/10/string").exists():
    subprocess.run(["python3", str(here / "prepare-sysroot.py")], check=True)
subprocess.run([str(clang), "--target=aarch64-linux-gnu", "--sysroot=" + str(sysroot),
                "-isystem", str(sysroot / "usr/include/c++/10"),
                "-isystem", str(sysroot / "usr/include/aarch64-linux-gnu/c++/10"),
                "-isystem", str(sysroot / "usr/include/aarch64-linux-gnu"),
                "-fuse-ld=lld", "-nostdlib", "-fPIC", "-shared", "-O2", "-std=c++17", "-mno-outline-atomics",
                "-Wall", "-Wextra", "-Werror", "-Wl,-z,relro,-z,now",
                str(here / "audiohal-qemu.cpp"), "-o", str(out / "libaudiohal-qemu.so")], check=True)
subprocess.run([str(clang), "--target=aarch64-linux-gnu", "--sysroot=" + str(sysroot),
                "-isystem", str(sysroot / "usr/include/c++/10"),
                "-isystem", str(sysroot / "usr/include/aarch64-linux-gnu/c++/10"),
                "-isystem", str(sysroot / "usr/include/aarch64-linux-gnu"),
                "-fuse-ld=lld", "-nostdlib", "-fPIC", "-shared", "-O2", "-std=c++17", "-mno-outline-atomics",
                "-Wall", "-Wextra", "-Werror", "-Wl,-z,relro,-z,now",
                str(here / "engineering-platform.cpp"), "-o", str(out / "libengineering-platform-qemu.so")], check=True)

subprocess.run([str(clang), "--target=aarch64-linux-gnu", "--sysroot=" + str(sysroot),
                "-isystem", str(sysroot / "usr/include/c++/10"),
                "-isystem", str(sysroot / "usr/include/aarch64-linux-gnu/c++/10"),
                "-isystem", str(sysroot / "usr/include/aarch64-linux-gnu"),
                "-fuse-ld=lld", "-nostdlib", "-fPIC", "-shared", "-O2", "-std=c++17", "-mno-outline-atomics",
                "-Wall", "-Wextra", "-Werror", "-Wl,-z,relro,-z,now",
                str(here / "app-launch.cpp"), "-o", str(out / "libapp-launch-qemu.so")], check=True)

subprocess.run([str(clang), "--target=aarch64-linux-gnu", "--sysroot=" + str(sysroot),
                "-isystem", str(sysroot / "usr/include/c++/10"),
                "-isystem", str(sysroot / "usr/include/aarch64-linux-gnu/c++/10"),
                "-isystem", str(sysroot / "usr/include/aarch64-linux-gnu"),
                "-fuse-ld=lld", "-nostdlib", "-fPIC", "-shared", "-O2", "-std=c++17", "-mno-outline-atomics",
                "-Wall", "-Wextra", "-Werror", "-Wl,-z,relro,-z,now",
                str(here / "media-platform.cpp"), "-o", str(out / "libmedia-platform-qemu.so")], check=True)
