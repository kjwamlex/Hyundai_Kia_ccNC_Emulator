#!/bin/sh
set -e
ccnc -ec 'python3 -u /opt/ccnc-qemu/audit-apps.py qiblahmi userprofilehmi extcamerahmi euradiohmi'
echo CCNC_CAPTURE_READY
sleep 1
