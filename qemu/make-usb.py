#!/usr/bin/env python3
"""Copy a research fixture directory into a raw ext4 USB image (never a package signer)."""
import argparse
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Directory whose contents go at USB root")
    parser.add_argument("output", type=Path, help="New raw image; existing files are refused")
    parser.add_argument("--size-mib", type=int, default=128)
    args = parser.parse_args()
    if not args.source.is_dir():
        parser.error("source must be a directory")
    if args.size_mib < 32:
        parser.error("minimum image size is 32 MiB")
    mkfs = shutil.which("mkfs.ext4") or "/opt/homebrew/opt/e2fsprogs/sbin/mkfs.ext4"
    if not Path(mkfs).is_file():
        parser.error("install e2fsprogs first")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.truncate(args.size_mib * 1024 * 1024)
    subprocess.run([mkfs, "-q", "-F", "-L", "CCNC_LAB", "-d", str(args.source.resolve()),
                    str(args.output.resolve())], check=True)
    print("Created fixture image:", args.output.resolve())


if __name__ == "__main__":
    main()
