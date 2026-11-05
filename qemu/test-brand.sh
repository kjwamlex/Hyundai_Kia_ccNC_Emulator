#!/bin/sh
set -eu
ccnc -ec '
test -f /run/ccnc-qemu/apps-ready
python3 - <<"PY"
import json
from pathlib import Path

saved = json.loads(Path("/ccos/data/ccnc-qemu/brand.json").read_text())["brand"]
expected = {"hyundai": "HYUNDAI", "kia": "KIA"}[saved]
actual = json.loads(Path("/tmp/ccos/sw_feature.json").read_text())["SW.CAR_BRAND"]
assert actual == expected, (actual, expected)
shared = Path("/dev/shm/variantstr1.mm").read_bytes()
assert ("SW.CAR_BRAND%" + expected + "&").encode() in shared
for kind in ("welcome", "goodbye"):
    clip = Path("/ccos/services/welcomeaniservice/lhd") / (kind + "_" + saved + "_avnt.264")
    assert clip.is_file(), clip
print("CCNC_BRAND_VERIFIED: " + expected)
PY
'
echo CCNC_CAPTURE_READY
sleep 1
