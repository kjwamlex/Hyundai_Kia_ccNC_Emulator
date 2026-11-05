#!/bin/sh
set -e
ccnc -ec 'python3 -u /opt/ccnc-qemu/audit-apps.py qiblahmi'
echo CCNC_CAPTURE_READY
sleep 1
