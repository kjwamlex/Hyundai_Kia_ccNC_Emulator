#!/bin/sh
set -e
mode=desktop
for arg in $(cat /proc/cmdline); do
    case "$arg" in ccnc.gui=*) mode=${arg#ccnc.gui=} ;; esac
done
modprobe virtio_gpu
modprobe xhci_pci
modprobe usbhid
modprobe hid_generic
modprobe evdev
if [ "$mode" = ccnc ]; then
    # The original status bar emits Back/Menu through a virtual input device.
    modprobe uinput
fi
# USB enumeration is asynchronous; udev cannot settle events not yet emitted.
i=0
while [ ! -e /dev/input/event0 ] && [ "$i" -lt 30 ]; do
    sleep 0.1
    i=$((i+1))
done
mkdir -p /dev/shm
mount -t tmpfs -o mode=1777 tmpfs /dev/shm
mount --bind /dev/shm /ccnc/dev/shm
ip link set lo up
if [ "$mode" = ccnc ]; then
    mount -t tmpfs tmpfs /sys/fs/cgroup
    mkdir -p /sys/fs/cgroup/cpu
    mount -t cgroup -o cpu,cpuacct cgroup /sys/fs/cgroup/cpu
    for group in ccos-active.slice ccos-deactive.slice ccos-system.slice; do
        mkdir -p /sys/fs/cgroup/cpu/ccos.slice/$group
    done
    echo 128 >/sys/fs/cgroup/cpu/ccos.slice/ccos-deactive.slice/cpu.shares
    mount --rbind /sys/fs/cgroup /ccnc/sys/fs/cgroup
fi
ccnc -c 'mkdir -p /run/udev; /lib/systemd/systemd-udevd --daemon; udevadm trigger; udevadm settle --timeout=5; udevadm trigger --action=add --subsystem-match=input; udevadm settle --timeout=5' >/run/udev-setup.log 2>&1 || cat /run/udev-setup.log
ccnc -c 'for device in /sys/class/input/event*; do udevadm test "$device" >/dev/null 2>&1; done'
ccnc -c "/opt/ccnc-qemu/start-gui.sh $mode"
