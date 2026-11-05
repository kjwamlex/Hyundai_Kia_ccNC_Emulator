#!/bin/sh
set -e
ccnc -ec '
test -f /run/ccnc-qemu/home-ready
for service in weston homehmi appeventmanager appservice userservice systemservice; do
    kill -0 "$(cat /run/ccnc-qemu/$service.pid)"
done
grep "homehmi - state: RUN, running state: FOREGROUND" /tmp/ccnc-qemu/dlt.log
grep "HomeFrontWindow: onVisible()" /tmp/ccnc-qemu/dlt.log
grep "event0.*device is a pointer" /tmp/ccnc-qemu/weston.log
grep -q libEGL_mesa /proc/$(cat /run/ccnc-qemu/homehmi.pid)/maps
grep -q swrast_dri /proc/$(cat /run/ccnc-qemu/homehmi.pid)/maps
! grep -q libnvidia-eglcore /proc/$(cat /run/ccnc-qemu/homehmi.pid)/maps
echo CCNC_HMI_GRAPHICS_OK
'
sleep 3
echo CCNC_CAPTURE_READY
sleep 1
echo CCNC_INPUT_READY
i=0
until ccnc -c 'grep -q "widgetMouseArea.onClicked.*widgetName:BTCall" /tmp/ccnc-qemu/dlt.log'; do
    i=$((i+1))
    if [ "$i" -ge 50 ]; then
        ccnc -c 'grep -E "widgetMouseArea|onClicked|onPressed|onReleased" /tmp/ccnc-qemu/dlt.log; tail -100 /tmp/ccnc-qemu/homehmi.log; cat /tmp/ccnc-qemu/weston.log'
        echo CCNC_POINTER_FAILED
        exit 1
    fi
    sleep 0.2
done
ccnc -c 'grep "widgetMouseArea.onClicked" /tmp/ccnc-qemu/dlt.log'
echo CCNC_POINTER_OK
