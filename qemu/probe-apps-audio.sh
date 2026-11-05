#!/bin/sh
set -e
ccnc /opt/ccnc-qemu/probe-apps-audio-inner.sh
echo CCNC_CAPTURE_READY
sleep 1
