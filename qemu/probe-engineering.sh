#!/bin/sh
set -e
ccnc -ec '
/opt/ccnc-qemu/open-app.sh engineering
sleep 5
for app in engineeringmodemanager engineeringmodehmi; do
    kill -0 "$(cat /run/ccnc-qemu/$app.pid)"
done
kill -0 "$(cat /run/ccnc-qemu/engineeringmodehmi.pid)"
! grep -q "signal: 11" /tmp/ccnc-qemu/engineeringmodehmi.log
grep "CHANGED : engineeringmodehmi - state: RUN" /tmp/ccnc-qemu/dlt.log | tail -1 | grep "running state: FOREGROUND"
grep "ENGMODE.FullKeyboard onCompleted" /tmp/ccnc-qemu/dlt.log | tail -1
echo CCNC_ENGINEERING_PASSWORD_READY
'
echo CCNC_CAPTURE_READY
sleep 1
