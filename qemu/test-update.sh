#!/bin/sh
set -e
ccnc -ec '
test -f /run/ccnc-qemu/apps-ready
test -f /run/ccnc-qemu/update-ready
for app in setuphmi updatehmi vehicleupdatehmi popupmanager; do
    kill -0 "$(cat /run/ccnc-qemu/$app.pid)"
done
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket
dbus-send --session --print-reply --dest=com.mobis.swupdate /com/mobis/swupdate com.mobis.swupdate.method_getUpdateEngineStatus
'
echo CCNC_UPDATE_SETTINGS
sleep 2
echo CCNC_UPDATE_GENERAL
sleep 2
# The original updater scans installed versions asynchronously on startup.
# Wait for its completion signal so this click tests package discovery, rather
# than the legitimate "version check in progress" response.
ccnc -ec '
i=0
until grep -q "UpdateSWUpdate: onScanVersion result:" /tmp/ccnc-qemu/dlt.log; do
    i=$((i+1))
    [ "$i" -lt 65 ] || { tail -80 /tmp/ccnc-qemu/updateservice.log; exit 1; }
    sleep 1
done
'
echo CCNC_UPDATE_CLICK
sleep 5
ccnc -ec '
log=/tmp/ccnc-qemu/dlt.log
grep -q "sendSWUpdatePrepare success:" "$log"
grep -q "\[onCall\] updateType is USB" "$log"
if [ -f /run/ccnc-qemu/usb-fstype ]; then
    test "$(cat /sys/block/sda/ro)" = 1
    grep -q " /run/media/USB_Front .*ro," /proc/mounts
    test -r /run/media/USB_Front/README.txt
    grep -E "USB|scanVersion|ScanVersion|MAINCONFIG|checkShowUpdatePopup|reqPopupWithStatus" "$log" | tail -55
    grep -Fq "APP_CHK**_USB**-PKG**_START-GROUP_1" "$log"
    echo CCNC_UPDATE_USB_PRESENT
else
    grep -q "\[checkShowUpdatePopup\] No USB mounted" "$log"
    echo CCNC_UPDATE_USB_ABSENT
fi
grep -q "\[reqPopupWithStatus\] pId: 3, sId: 4" "$log"
grep -q "Update internal popup model is opened" "$log"
grep -q "cameraViewMode:camera_off" "$log"
python3 /opt/ccnc-qemu/window-dump.py --expect-update visible
grep -E "APP_REQUEST_UPDATE|reqPopupWithStatus|PopupModel|createPopup|openPopup" "$log" | tail -35
cat /tmp/ccnc-qemu/lab-state.log
'
echo CCNC_UPDATE_DISMISS
sleep 2
ccnc -ec 'python3 /opt/ccnc-qemu/window-dump.py --expect-update hidden'
echo CCNC_UPDATE_REOPEN
sleep 3
ccnc -ec 'python3 /opt/ccnc-qemu/window-dump.py --expect-update visible'
echo CCNC_CAPTURE_READY
sleep 1
