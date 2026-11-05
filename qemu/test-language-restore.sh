#!/bin/sh
set -e
ccnc -ec '
test -f /run/ccnc-qemu/apps-ready
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket
python3 /opt/ccnc-qemu/check-language.py 1
grep -q "CCNC_LANGUAGE_READY: type=1 restored=True" /tmp/ccnc-qemu/language-state.log
grep -q "changed:en_US" /tmp/ccnc-qemu/dlt.log
python3 /opt/ccnc-qemu/window-dump.py --expect-window HOME.APPLICATION visible
cat /tmp/ccnc-qemu/language-state.log
'
echo CCNC_CAPTURE_READY
sleep 1
echo CCNC_LANGUAGE_RESTORE_OK
