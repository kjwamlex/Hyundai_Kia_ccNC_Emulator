#!/bin/sh
set -e
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket
export LD_PRELOAD=/opt/ccnc-qemu/libashmem-qemu.so:/ccos/lib/libtrace.so
export VSOMEIP_APPLICATION_NAME=updateservice
export VSOMEIP_CONFIGURATION=/ccos/daemons/routingmanagerd/vsomeip.json
mkdir -p /ccos/data/log/updatelog /ccos/data/update
(cd /ccos/services/updateservice && exec ./updateservice) >/tmp/ccnc-qemu/updateservice.log 2>&1 &
echo $! >/run/ccnc-qemu/updateservice.pid
i=0
until dbus-send --session --print-reply --reply-timeout=1000 --dest=com.mobis.swupdate /com/mobis/swupdate org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1; do
    kill -0 "$(cat /run/ccnc-qemu/updateservice.pid)"
    i=$((i+1))
    [ "$i" -lt 80 ] || exit 1
    sleep 0.1
done
touch /run/ccnc-qemu/update-ready
echo 'CCNC_UPDATE_SERVICE_READY: original com.mobis.swupdate'
