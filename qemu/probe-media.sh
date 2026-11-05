#!/bin/sh
# Read-only diagnostics against the media stack started by --gui ccnc.
set -e
ccnc -c '
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket
for method in getNowPlayingInfo getNowPlayingStatus; do
    dbus-send --session --print-reply --reply-timeout=3000 --dest=ccos.app.manager.mediagatemanager.NowPlaying /ccos/app/manager/mediagatemanager/NowPlaying ccos.app.manager.mediagatemanager.NowPlaying.$method int32:8
done
dbus-send --session --print-reply --reply-timeout=3000 --dest=ccos.app.manager.mediagatemanager.NowPlaying /ccos/app/manager/mediagatemanager/NowPlaying ccos.app.manager.mediagatemanager.NowPlaying.getLastMediaInfo int32:8 int32:0
/opt/ccnc-qemu/open-app.sh tone
sleep 12
/opt/ccnc-qemu/open-app.sh audio
sleep 3
for service in audioservice mediaservice mediagatemanager audiohmi mediahomehmi phonehmi; do
    echo "=== $service ==="
    kill -0 "$(cat /run/ccnc-qemu/$service.pid)"
    tail -20 /tmp/ccnc-qemu/$service.log
done
dbus-send --session --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames
grep -E "ECU1 AUDI|ECU1 APPS|ECU1 aem-.*(Audio|AUDIO|audio|launch|Launch)|audiohmi|MEDIA.Audio|LaunchApp" /tmp/ccnc-qemu/dlt.log | tail -150
grep -E "ECU1 HOME.*(NowPlaying|nowPlaying|initNow|AvOff|Exception|e:)" /tmp/ccnc-qemu/dlt.log | tail -50
'
echo CCNC_CAPTURE_READY
sleep 1
