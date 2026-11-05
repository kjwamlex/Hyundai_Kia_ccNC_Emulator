#!/bin/busybox sh
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
/bin/busybox --install -s /bin
mkdir -p /proc /sys /dev /run /firmware /ccnc /scratch
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
exec </dev/ttyAMA0 >/dev/ttyAMA0 2>&1
mkdir -p /dev/pts
mount -t devpts devpts /dev/pts
mount -t tmpfs tmpfs /run

rescue() {
    echo "CCNC_SETUP_FAILED: $*"
    case " $(cat /proc/cmdline) " in
        *" ccnc.smoke=1 "*) poweroff -f; while :; do sleep 1; done ;;
    esac
    exec setsid /bin/sh -c 'exec /bin/sh -i </dev/ttyAMA0 >/dev/ttyAMA0 2>&1'
}

modprobe virtio_pci || rescue virtio_pci
modprobe virtio_blk || rescue virtio_blk
modprobe ext4 || rescue ext4
modprobe overlay || rescue overlay
i=0
while [ ! -b /dev/vda ] && [ "$i" -lt 50 ]; do sleep 0.1; i=$((i+1)); done
[ -b /dev/vda ] || rescue "firmware disk /dev/vda missing"
mount -t ext4 -o ro,noload /dev/vda /firmware || rescue "mount firmware"
case " $(cat /proc/cmdline) " in
    *" ccnc.state=1 "*)
        i=0
        while [ ! -b /dev/vdb ] && [ "$i" -lt 50 ]; do sleep 0.1; i=$((i+1)); done
        [ -b /dev/vdb ] || rescue "state disk /dev/vdb missing"
        mount -t ext4 -o rw /dev/vdb /ccnc || rescue "mount writable state disk"
        firmware_mode='persistent read/write disk (changes survive shutdown)'
        ;;
    *)
        mount -t tmpfs -o size=768m tmpfs /scratch || rescue "scratch RAM"
        mkdir -p /scratch/upper /scratch/work
        mount -t overlay overlay -o lowerdir=/firmware,upperdir=/scratch/upper,workdir=/scratch/work /ccnc || rescue "overlay"
        firmware_mode='disposable RAM write layer (changes lost on shutdown)'
        ;;
esac
mkdir -p /ccnc/proc /ccnc/sys /ccnc/dev /ccnc/run /ccnc/tmp
mount --bind /proc /ccnc/proc
mount --bind /sys /ccnc/sys
mount --rbind /dev /ccnc/dev
mount -t tmpfs tmpfs /ccnc/run
mount -t tmpfs tmpfs /ccnc/tmp
if [ -d /ccnc-payload ]; then
    cp -a /ccnc-payload/. /ccnc/
fi
export TERM=vt100
case " $(cat /proc/cmdline) " in
    *" ccnc.audio=1 "*)
        modprobe snd_hda_intel
        modprobe snd_hda_codec_generic
        if [ -f /ccnc/opt/ccnc-qemu/asound.conf ]; then
            cp /ccnc/opt/ccnc-qemu/asound.conf /ccnc/etc/asound.conf
        fi
        ;;
esac
for arg in $(cat /proc/cmdline); do
    case "$arg" in ccnc.epoch=*) date -u -s "@${arg#ccnc.epoch=}" >/dev/null ;; esac
done
case " $(cat /proc/cmdline) " in
    *" ccnc.usb=1 "*)
        modprobe xhci_pci || rescue usb-xhci
        modprobe usb_storage || rescue usb-storage
        modprobe sd_mod || rescue usb-disk
        modprobe vfat
        modprobe exfat
        mkdir -p /ccnc/run/media/USB_Front /ccnc/run/ccnc-qemu
        i=0
        while [ ! -b /dev/sda ] && [ "$i" -lt 100 ]; do sleep 0.1; i=$((i+1)); done
        [ -b /dev/sda ] || rescue "USB disk /dev/sda missing"
        [ "$(cat /sys/block/sda/ro)" = 1 ] || rescue "USB disk must be read-only"
        usb_volume=/dev/sda
        [ ! -b /dev/sda1 ] || usb_volume=/dev/sda1
        usb_type=$(blkid "$usb_volume" | sed -n 's/.* TYPE="\([^"]*\)".*/\1/p')
        case "$usb_type" in
            ext4) usb_options=ro,noload,nosuid,nodev,noexec ;;
            vfat|exfat) usb_options=ro,nosuid,nodev,noexec ;;
            *) rescue "Unsupported USB filesystem: $usb_type" ;;
        esac
        mount -t "$usb_type" -o "$usb_options" "$usb_volume" /ccnc/run/media/USB_Front || rescue usb-mount
        printf '%s\n' "$usb_type" >/ccnc/run/ccnc-qemu/usb-fstype
        echo "CCNC_USB_MOUNTED: $usb_volume read-only at /run/media/USB_Front ($usb_type)"
        ;;
esac
if [ -f /ccnc-gui.sh ]; then
    /bin/sh /ccnc-gui.sh || echo 'CCNC_GRAPHICS_SETUP_FAILED: inspect the serial output'
fi
echo
echo 'ccNC ARM64 userspace sandbox ready.'
echo 'ccnc            enter the original firmware shell'
echo 'ccnc -c COMMAND run a command with the firmware libraries'
echo '/firmware       original filesystem (read-only)'
echo "/ccnc           firmware with a $firmware_mode"
echo 'poweroff -f     stop the VM; Ctrl-a x also exits QEMU'
echo 'Tegra GPU, hypervisor and vehicle peripherals are not emulated.'
echo
if [ -f /ccnc-job.sh ]; then
    /bin/sh /ccnc-job.sh
    echo "CCNC_JOB_EXIT=$?"
    sync
    sleep 0.2
    poweroff -f
    while :; do sleep 1; done
fi
case " $(cat /proc/cmdline) " in
    *" ccnc.smoke=1 "*)
        ccnc -ec 'echo CCNC_USERSPACE_BEGIN; test "$(/bin/uname -m)" = aarch64; /bin/uname -m; /bin/cat /etc/os-release; test -d /ccos/apps; test -d /ccos/services; /bin/ls /; echo ram-overlay-test > /etc/.qemu-smoke'
        status=$?
        if [ "$status" -eq 0 ]; then
            [ "$(cat /sys/block/vda/ro)" = 1 ] &&
            [ -f /ccnc/etc/.qemu-smoke ] &&
            [ ! -e /firmware/etc/.qemu-smoke ] || status=1
        fi
        rm -f /ccnc/etc/.qemu-smoke
        [ "$status" -ne 0 ] || echo CCNC_USERSPACE_OK
        echo "CCNC_SMOKE_EXIT=$status"
        sync
        sleep 0.2
        poweroff -f
        while :; do sleep 1; done
        ;;
esac
while :; do
    setsid /bin/sh -c 'exec /bin/sh -i </dev/ttyAMA0 >/dev/ttyAMA0 2>&1'
    sleep 0.1
done
