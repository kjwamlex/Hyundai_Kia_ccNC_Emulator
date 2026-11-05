#!/usr/bin/env python3
"""Install a pinned Debian ARM64 CPU OpenGL stack in the disposable payload."""
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / "artifacts/mesa"
DEST = HERE.parent / "overrides/opt/ccnc-qemu/mesa"


def data_archive(blob):
    if blob[:8] != b"!<arch>\n":
        raise ValueError("Not a Debian ar archive")
    offset = 8
    while offset + 60 <= len(blob):
        header = blob[offset:offset + 60]
        size = int(header[48:58])
        name = header[:16].decode().strip().rstrip("/")
        offset += 60
        if name.startswith("data.tar"):
            return blob[offset:offset + size]
        offset += size + (size % 2)
    raise ValueError("No data archive")


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)
    for driver in (DEST / "lib/dri").glob("*"):
        driver.unlink()
    for package in json.loads((HERE / "mesa-sources.json").read_text()):
        cached = CACHE / package["url"].rsplit("/", 1)[1]
        if not cached.exists():
            urllib.request.urlretrieve(package["url"], cached)
        blob = cached.read_bytes()
        if hashlib.sha256(blob).hexdigest() != package["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {cached}")
        with tarfile.open(fileobj=io.BytesIO(data_archive(blob))) as archive:
            # Preserve the library subtree, including dri/ and relative symlinks.
            for member in archive:
                name = member.name.removeprefix("./")
                prefix = next((p for p in ("usr/lib/aarch64-linux-gnu/", "lib/aarch64-linux-gnu/") if name.startswith(p)), None)
                if not prefix:
                    continue
                relative = Path(name[len(prefix):])
                if relative.parts[0] == "dri" and relative.name != "swrast_dri.so":
                    continue
                if ".." in relative.parts or relative.is_absolute():
                    raise ValueError(name)
                target = DEST / "lib" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if member.isdir():
                    target.mkdir(exist_ok=True)
                elif member.issym():
                    target.unlink(missing_ok=True)
                    target.symlink_to(member.linkname)
                elif member.islnk():
                    linked = member.linkname.removeprefix("./")
                    if not linked.startswith(prefix) or ".." in Path(linked).parts:
                        raise ValueError(linked)
                    target.unlink(missing_ok=True)
                    target.write_bytes(archive.extractfile(member).read())
                    target.chmod(member.mode)
                elif member.isfile():
                    target.write_bytes(archive.extractfile(member).read())
                    target.chmod(member.mode)
        print(package["package"], package["version"])
    (DEST / "egl.json").write_text(json.dumps({"file_format_version": "1.0.0", "ICD": {
        "library_path": "/opt/ccnc-qemu/mesa/lib/libEGL_mesa.so.0"}}) + "\n")
    print(DEST)


if __name__ == "__main__":
    main()
