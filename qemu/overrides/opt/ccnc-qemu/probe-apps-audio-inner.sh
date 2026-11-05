#!/bin/sh
# Run after the normal dashboard startup; never start duplicate service instances.
set -e
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket
test -f /run/ccnc-qemu/apps-ready
cat /proc/asound/cards
amixer -c 0 scontents
/opt/ccnc-qemu/open-app.sh tone
/opt/ccnc-qemu/open-app.sh media
sleep 3
for service in audioservice mediaservice mediagatemanager rfconnsetuphmi phonehmi audiohmi mediahomehmi; do
    echo "=== $service ==="
    kill -0 "$(cat /run/ccnc-qemu/$service.pid)"
    tail -20 /tmp/ccnc-qemu/$service.log
done
ls -l /tmp/ccos.audio.*
grep -E "state: RUN|ANR signal|is killed|onVisible" /tmp/ccnc-qemu/dlt.log | tail -60
