#!/bin/sh
set -e
ccnc -ec '
test -f /run/ccnc-qemu/apps-ready
test -c /dev/uinput
for service in statusbarhmi window-input-router; do
    kill -0 "$(cat /run/ccnc-qemu/$service.pid)"
done
'
window() {
    ccnc -ec "python3 /opt/ccnc-qemu/window-dump.py --expect-window $1 $2"
}
scene() {
    ccnc -ec "grep 'setCurrentScene(): sceneId:' /tmp/ccnc-qemu/dlt.log | tail -1 | grep -F 'sceneId: $1]'"
}
foreground() {
    ccnc -ec "grep 'CHANGED : $1 - state: RUN' /tmp/ccnc-qemu/dlt.log | tail -1 | grep 'running state: FOREGROUND'"
}
echo CCNC_NAV_SETTINGS
sleep 2
foreground setuphmi
scene SETUP.Gate
window STATUSBAR.BOTTOMBAR_LEFT visible
echo CCNC_NAV_GENERAL
sleep 2
scene SETUP.General.Main
echo CCNC_NAV_BACK
sleep 2
scene SETUP.Gate
echo CCNC_NAV_MENU
sleep 1
window SETUP.OPTIONMENU visible
echo CCNC_NAV_MENU_SHOT
sleep 1
echo CCNC_NAV_DISMISS
sleep 1
window SETUP.OPTIONMENU hidden
echo CCNC_NAV_REOPEN
sleep 1
window SETUP.OPTIONMENU visible
echo CCNC_CAPTURE_READY
sleep 1
echo CCNC_NAV_HOME
sleep 2
foreground homehmi
window SETUP.OPTIONMENU hidden
echo CCNC_NAV_MEDIA
sleep 2
foreground mediahomehmi
window MEDIAHOME.APPLICATION visible
window STATUSBAR.BOTTOMBAR_LEFT visible
echo CCNC_NAV_MEDIA_HOME
sleep 2
foreground homehmi
window MEDIAHOME.APPLICATION hidden
echo CCNC_NAVIGATION_OK
