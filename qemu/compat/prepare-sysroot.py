#!/usr/bin/env python3
"""Prepare pinned ARM64 GNU C++ headers for the userspace audio adapter."""
import hashlib, io, json, tarfile, urllib.request, importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('mesa', HERE / 'prepare-mesa.py')
mesa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mesa)
dest = HERE.parent / 'artifacts/sysroot'
cache = HERE.parent / 'artifacts/toolchain'
cache.mkdir(parents=True, exist_ok=True)
dest.mkdir(parents=True, exist_ok=True)
for pkg in json.loads((HERE / 'sysroot-sources.json').read_text()):
    path = cache / pkg['url'].rsplit('/',1)[1]
    if not path.exists(): urllib.request.urlretrieve(pkg['url'], path)
    blob = path.read_bytes()
    if hashlib.sha256(blob).hexdigest() != pkg['sha256']: raise ValueError(str(path))
    with tarfile.open(fileobj=io.BytesIO(mesa.data_archive(blob))) as archive:
        archive.extractall(dest, filter='tar')
    print(pkg['package'], pkg['version'])
