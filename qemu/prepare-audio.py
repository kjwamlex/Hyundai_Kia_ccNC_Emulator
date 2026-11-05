#!/usr/bin/env python3
"""Build a sound-capable Alpine LTS boot path, with a minimal module closure."""
import gzip
import hashlib
import io
import json
import stat
import tarfile
import urllib.request
from pathlib import Path
from prepare import cpio_entry, HERE, ART


def main():
    source, = json.loads((HERE / "audio-sources.json").read_text())
    cache = ART / "alpine" / source["file"]
    if not cache.exists():
        urllib.request.urlretrieve(source["url"], cache)
    if hashlib.sha256(cache.read_bytes()).hexdigest() != source["sha256"]:
        raise ValueError("Sound kernel APK SHA-256 mismatch")
    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(cache.read_bytes())), mode="r:", ignore_zeros=True) as archive:
        files = {m.name.removeprefix("./"): m for m in archive if m.isfile()}
        dep_name = next(n for n in files if n.endswith("/modules.dep"))
        module_root = dep_name.rsplit("/", 1)[0] + "/"
        dependencies = dict(line.split(":", 1) for line in archive.extractfile(files[dep_name]).read().decode().splitlines())
        wanted = {"virtio_pci", "virtio_blk", "ext4", "overlay", "virtio_gpu", "xhci_pci",
                  "usbhid", "hid_generic", "evdev", "uinput", "snd_hda_intel", "snd_hda_codec_generic",
                  "crc32c_generic", "crc32_generic", "usb_storage", "sd_mod", "vfat",
                  "nls_cp437", "nls_iso8859_1", "exfat"}
        selected = set()

        def add(name):
            if name in selected:
                return
            selected.add(name)
            for dependency in dependencies[name].split():
                add(dependency)

        for name in dependencies:
            stem = Path(name).name.split(".ko")[0].replace("-", "_")
            if stem in wanted:
                add(name)
        additions = bytearray()
        selected_files = {module_root + n for n in selected}
        selected_files.update(n for n in files if n.startswith(module_root + "modules."))
        directories = {str(p) for n in selected_files for p in Path(n).parents if str(p) != "."}
        for name in sorted(directories):
            additions += cpio_entry(name, mode=stat.S_IFDIR | 0o755)
        for name in sorted(selected_files):
            additions += cpio_entry(name, archive.extractfile(files[name]).read(), stat.S_IFREG | 0o644)
        (ART / "alpine/vmlinuz-lts").write_bytes(archive.extractfile(files["boot/vmlinuz-lts"]).read())
        additions += cpio_entry("init", (HERE / "guest-init.sh").read_bytes())
        additions += cpio_entry("bin/ccnc", b'#!/bin/sh\nexport PATH=/usr/sbin:/usr/bin:/sbin:/bin\nexec chroot /ccnc /bin/sh "$@"\n')
        additions += cpio_entry("TRAILER!!!", mode=0)
        base = gzip.decompress((ART / "alpine/initramfs-virt").read_bytes())
        base += b"\0" * (-len(base) % 4)
        (ART / "ccnc-audio-initramfs.cpio.gz").write_bytes(gzip.compress(base + additions, mtime=0))
        print(f"Prepared LTS audio kernel and {len(selected)} modules")


if __name__ == "__main__":
    main()
