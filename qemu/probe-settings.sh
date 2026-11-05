#!/bin/sh
set -e
ccnc -ec '
/opt/ccnc-qemu/open-app.sh settings
sleep 6
kill -0 "$(cat /run/ccnc-qemu/setuphmi.pid)"
grep "CHANGED : setuphmi - state: RUN" /tmp/ccnc-qemu/dlt.log | tail -1 | grep "running state: FOREGROUND"
cat /tmp/ccnc-qemu/setuphmi.log
grep -E "setuphmi|ECU1 SETU" /tmp/ccnc-qemu/dlt.log | tail -90
'
echo CCNC_CAPTURE_READY
sleep 1
