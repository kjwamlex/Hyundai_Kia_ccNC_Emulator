#!/bin/sh
set -e
ccnc -ec 'test -f /run/ccnc-qemu/apps-ready; python3 -u /opt/ccnc-qemu/audit-apps.py --scenes alexavrhmi androidautohmi carlifehmi carpayhmi carplayhmi cartohomehmi carwashmodehmi ccscontentshmi ccshmi connectedgaragehmi cvccshmi dashcamerahmi ecallhmi extcamerahmi hipasshmi locationsharinghmi petcarehmi qiblahmi radiohmi smartthingshmi sportshmi streaminghmi theaterhmi trailermodehmi usbvideohmi voicememohmi vrhmi weatherhmi webcommonhmi webosprojectionhmi'
echo CCNC_CAPTURE_READY
sleep 1
