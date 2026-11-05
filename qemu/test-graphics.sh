#!/bin/sh
set -e
sleep 1
ccnc -ec '
export XDG_RUNTIME_DIR=/run/user/0 WAYLAND_DISPLAY=wayland-system
test -c /dev/fb0
test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"
kill -0 "$(cat /run/ccnc-qemu/weston.pid)"
kill -0 "$(cat /run/ccnc-qemu/client.pid)"
weston-info
cat /tmp/ccnc-qemu/weston.log
cat /tmp/ccnc-qemu/simple-shm.log
echo "=== input devices ==="
cat /proc/bus/input/devices
udevadm info -q property -n /dev/input/event0
udevadm test /sys/class/input/event0 2>&1 | tail -60
cat /etc/udev/rules.d/99-qemu-input.rules
echo CCNC_GRAPHICS_OK
'
echo CCNC_CAPTURE_READY
sleep 2
