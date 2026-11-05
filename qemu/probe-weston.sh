#!/bin/sh
set -e
modprobe virtio_gpu
modprobe usbhid
modprobe xhci_pci
ccnc -c '
export XDG_RUNTIME_DIR=/run/user/0
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
export WAYLAND_DISPLAY=wayland-qemu
weston --no-config --backend=fbdev-backend.so --device=/dev/fb0 --tty=2 --shell=desktop-shell.so --socket=wayland-qemu --idle-time=0 --log=/tmp/weston-qemu.log &
weston_pid=$!
sleep 2
cat /tmp/weston-qemu.log
if ! kill -0 "$weston_pid"; then exit 1; fi
weston-info
weston-simple-shm >/tmp/simple-shm.log 2>&1 &
sleep 2
cat /tmp/simple-shm.log
echo CCNC_CAPTURE_READY
sleep 8
kill "$weston_pid"
'
