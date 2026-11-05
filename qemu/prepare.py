#!/usr/bin/env python3
"""Recover vendor boot payloads and build the QEMU userspace sandbox initramfs."""
import gzip
import hashlib
import io
import json
import shutil
import stat
import struct
import subprocess
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ART = HERE / "artifacts"


def lz4_frame(data):
    """Find the exact frame end, excluding NVIDIA alignment padding."""
    if data[:4] != b"\x04\x22\x4d\x18":
        raise ValueError("Expected an LZ4 frame after the two 512-byte headers")
    flags = data[4]
    offset = 7 + (8 if flags & 8 else 0) + (4 if flags & 1 else 0)
    while True:
        size = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        if size == 0:
            break
        offset += (size & 0x7fffffff) + (4 if flags & 16 else 0)
        if offset > len(data):
            raise ValueError("Truncated LZ4 frame")
    offset += 4 if flags & 4 else 0
    return data[:offset]


def cpio_entry(name, data=b"", mode=stat.S_IFREG | 0o755, inode=1):
    name = name.encode() + b"\0"
    fields = [inode, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(name), 0]
    header = b"070701" + b"".join(f"{v:08x}".encode() for v in fields)
    result = header + name
    result += b"\0" * (-len(result) % 4)
    result += data
    return result + b"\0" * (-len(data) % 4)


def main():
    vendor = ART / "vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    for source, output in [
        ("1_5_kernel_zerosign.img", "Image"),
        ("2_5_kernel_zerosign.img", "Image-recovery"),
        ("2_6_ramdisk_zerosign.img", "initramfs-recovery.cpio"),
    ]:
        data = (ROOT / "system" / source).read_bytes()
        if not data.startswith(b"BOOT_IMAGE!\0") or data[512:516] != b"GSHV":
            raise ValueError(f"Unexpected boot header: {source}")
        result = subprocess.run(["lz4", "-d", "-c"], input=lz4_frame(data[1024:]),
                                stdout=subprocess.PIPE, check=True)
        (vendor / output).write_bytes(result.stdout)
    for source, output in [("1_4_tegra_dtb_zerosign.dtb", "ccnc.dtb"),
                           ("2_4_tegra_dtb_zerosign.dtb", "recovery.dtb")]:
        data = (ROOT / "system" / source).read_bytes()[512:]
        if data[:4] != b"\xd0\x0d\xfe\xed":
            raise ValueError(f"Unexpected DTB: {source}")
        (vendor / output).write_bytes(data[:struct.unpack_from(">I", data, 4)[0]])
        if shutil.which("dtc"):
            with (vendor / output.replace(".dtb", ".dts")).open("wb") as stream:
                subprocess.run(["dtc", "-q", "-I", "dtb", "-O", "dts", str(vendor / output)],
                               stdout=stream, check=True)
    image = (vendor / "Image").read_bytes()
    start = image.index(b"IKCFG_ST") + 8
    end = image.index(b"IKCFG_ED", start)
    (vendor / "kernel.config").write_bytes(gzip.decompress(image[start:end]))

    alpine = ART / "alpine"
    alpine.mkdir(parents=True, exist_ok=True)
    sources = json.loads((HERE / "sources.json").read_text())
    for source in sources:
        path = alpine / source["file"]
        if not path.exists():
            print(f"Downloading {source['url']}", flush=True)
            data = urllib.request.urlopen(source["url"], timeout=180).read()
            if hashlib.sha256(data).hexdigest() != source["sha256"]:
                raise ValueError(f"Download hash mismatch: {path.name}; upstream may have changed")
            path.write_bytes(data)
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"Cache hash mismatch: {path}")

    # Alpine's netboot initramfs omits ext4. Supply matching modules from linux-virt.
    archive = gzip.decompress((alpine / "initramfs-virt").read_bytes())
    additions = bytearray()
    apk = alpine / next(s["file"] for s in sources if s["file"].endswith(".apk"))
    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(apk.read_bytes())), mode="r:", ignore_zeros=True) as tf:
        for member in tf:
            name = member.name.removeprefix("./")
            if name.startswith("lib/modules/"):
                if member.isdir():
                    additions += cpio_entry(name, mode=stat.S_IFDIR | 0o755)
                elif member.isfile():
                    additions += cpio_entry(name, tf.extractfile(member).read(), stat.S_IFREG | 0o644)
    additions += cpio_entry("init", (HERE / "guest-init.sh").read_bytes())
    additions += cpio_entry("bin/ccnc", b'#!/bin/sh\nexport PATH=/usr/sbin:/usr/bin:/sbin:/bin\nexec chroot /ccnc /bin/sh "$@"\n')
    additions += cpio_entry("TRAILER!!!", mode=0)
    archive += b"\0" * (-len(archive) % 4)
    (ART / "ccnc-initramfs.cpio.gz").write_bytes(gzip.compress(archive + additions, mtime=0))
    print("Prepared vendor payloads and QEMU initramfs.")


if __name__ == "__main__":
    main()
