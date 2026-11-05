#!/bin/sh
modprobe virtio_gpu
modprobe usbhid
modprobe xhci_pci
echo '=== Virtual graphics ==='
ls -l /dev/dri /dev/fb* /dev/tty0
ccnc -c '
echo "=== Weston options ==="
weston --help
echo "=== Qt configuration ==="
cat /etc/qt.conf /etc/ld.so.conf /etc/ld.so.conf.d/* 2>/dev/null
find /usr/lib -name "libq*wayland*" -o -name "*ivi*shell*" -o -name "libq*offscreen*" -o -name "libqlinuxfb*"
echo "=== Environment files ==="
ls /etc/profile.d
cat /etc/profile.d/* 2>/dev/null
echo "=== Weston clients ==="
ls /usr/bin/weston*
echo "=== HMI loader ==="
/lib/ld-linux-aarch64.so.1 --list /ccos/apps/hmi/homehmi/homehmi
echo "=== Display probe complete ==="
'
