#!/bin/sh
# Share the lab's startup/readiness handling with dashboard launch requests.
set -e
exec python3 /opt/ccnc-qemu/app-launcher.py --ensure engineeringmodehmi
