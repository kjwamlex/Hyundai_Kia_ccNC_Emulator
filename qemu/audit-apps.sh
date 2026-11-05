#!/bin/sh
set -e
ccnc -ec 'test -f /run/ccnc-qemu/apps-ready; python3 -u /opt/ccnc-qemu/audit-apps.py'
echo CCNC_CAPTURE_READY
sleep 1
