#!/bin/sh
set -e
# Settings writes preferences through this original manager, which forwards
# language changes to HSystem and notifies the original app translation clients.
(cd /ccos/apps/manager/setupmanager
    export VSOMEIP_APPLICATION_NAME=setupmanager
    export VSOMEIP_CONFIGURATION=/ccos/daemons/routingmanagerd/vsomeip.json
    exec ./setupmanager) >/tmp/ccnc-qemu/setupmanager.log 2>&1 &
echo $! >/run/ccnc-qemu/setupmanager.pid
i=0
until dbus-send --session --print-reply --reply-timeout=1000 --dest=ccos.sys.setupmanager.SetupSystem /ccos/sys/setupmanager/SetupSystem org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1; do
    kill -0 "$(cat /run/ccnc-qemu/setupmanager.pid)"
    i=$((i+1))
    if [ "$i" -ge 100 ]; then
        echo 'CCNC_SETTINGS_ERROR: original setupmanager did not become ready'
        cat /tmp/ccnc-qemu/setupmanager.log
        exit 1
    fi
    sleep 0.2
done
touch /run/ccnc-qemu/settings-ready
echo 'CCNC_SETTINGS_READY: original setupmanager language/preferences backend'
