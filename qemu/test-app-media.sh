#!/bin/sh
# Check optional media apps, then actual OEM audio playback in the same VM.
set -e
ccnc -ec 'python3 -u /opt/ccnc-qemu/audit-apps.py --scenes ccshmi radiohmi theaterhmi voicememohmi streaminghmi usbvideohmi petcarehmi weatherhmi webosprojectionhmi'
/bin/sh /ccnc/opt/ccnc-qemu/test-routing.sh
