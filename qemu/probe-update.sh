#!/bin/sh
# Inspect the already-running original updater; do not start duplicate services.
set -e
ccnc -ec '
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket
test -f /run/ccnc-qemu/update-ready
echo CCNC_UPDATE_INTROSPECTION
dbus-send --session --print-reply --reply-timeout=3000 --dest=com.mobis.swupdate /com/mobis/swupdate org.freedesktop.DBus.Introspectable.Introspect
echo CCNC_UPDATE_ENGINE
dbus-send --session --print-reply --dest=com.mobis.swupdate /com/mobis/swupdate com.mobis.swupdate.method_getUpdateEngineStatus
echo CCNC_UPDATE_LAB_INPUTS
cat /tmp/ccnc-qemu/lab-state.log
grep -E "ECU1 UPDA OTAI|ECU1 UPSE" /tmp/ccnc-qemu/dlt.log | tail -65
'
echo CCNC_CAPTURE_READY
sleep 1
