#!/bin/sh
modprobe virtio_gpu
modprobe usbhid
modprobe xhci_pci
mkdir -p /dev/shm
mount -t tmpfs tmpfs /dev/shm
mount --bind /dev/shm /ccnc/dev/shm
mount -t tmpfs tmpfs /sys/fs/cgroup
for controller in cpu,cpuacct pids freezer blkio devices; do
    name=${controller%%,*}
    mkdir -p /sys/fs/cgroup/$name
    mount -t cgroup -o "$controller" cgroup /sys/fs/cgroup/$name
done
mkdir -p /sys/fs/cgroup/systemd
mount -t cgroup -o none,name=systemd cgroup /sys/fs/cgroup/systemd
for group in ccos-active.slice ccos-deactive.slice ccos-system.slice; do
    mkdir -p /sys/fs/cgroup/cpu/ccos.slice/$group
done
mount --rbind /sys/fs/cgroup /ccnc/sys/fs/cgroup
ccnc -c '
export XDG_RUNTIME_DIR=/run
export WAYLAND_DISPLAY=wayland-system
export QT_QPA_PLATFORM=wayland
export QT_QUICK_BACKEND=software
export QT_WAYLAND_SHELL_INTEGRATION=ivi-shell
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1
export QML2_IMPORT_PATH=/ccos/apps/share/qml:/ccos/apps/share/plugins
export QT_PLUGIN_PATH=/ccos/apps/share/plugins:/usr/lib/plugins
export XDG_CACHE_HOME=/ccos/data/apps/.cache
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket
chmod 700 /run
mkdir -p /run/dbus /var/volatile/log /var/volatile/tmp /ccos/data/apps/.cache /tmp
ip link set lo up
echo "=== CPU cgroups ==="
cgget -a ccos.slice/ccos-active.slice
dbus-daemon --system --fork --nopidfile
dbus-daemon --session --fork --address="$DBUS_SESSION_BUS_ADDRESS"
cp /etc/dlt.conf /tmp/qemu-dlt.conf
printf "\nPrintASCII = 1\n" >>/tmp/qemu-dlt.conf
dlt-daemon -c /tmp/qemu-dlt.conf >/tmp/dlt-ascii.log 2>&1 &
echo "=== framework env ==="
cat /etc/xdg/systemd/fw-global-env.conf
set -a
. /etc/xdg/systemd/fw-global-env.conf
set +a
export LD_PRELOAD=/opt/ccnc-qemu/libashmem-qemu.so:$LD_PRELOAD
for svc in shareddataservice memoryservice persistenceservice appservice userservice variantservice clockservice; do
    (cd /ccos/services/$svc && ./$svc) >/tmp/$svc.log 2>&1 &
    sleep 1
done
sleep 2
(cd /ccos/apps/manager/appeventmanager && ./appeventmanager) >/tmp/appeventmanager.log 2>&1 &
echo "=== tools ==="
ls /usr/bin/strace /usr/bin/qml* /usr/bin/dbus* /usr/bin/dlt* 2>/dev/null
cat >/tmp/qemu-weston.ini <<EOF
[core]
idle-time=0
shell=ivi-shell.so
modules=/ccos/lib/window-manager-service.so
[ccos]
window-manager-policy=/ccos/lib/window-manager-policy.so
EOF
weston --config=/tmp/qemu-weston.ini --backend=fbdev-backend.so --device=/dev/fb0 --tty=2 --socket=wayland-system --log=/tmp/weston-hmi.log &
wpid=$!
sleep 2
cat /tmp/weston-hmi.log
echo "=== compositor globals ==="
weston-info
echo "=== launching homehmi ==="
cd /ccos/apps/hmi/homehmi
./homehmi >/tmp/homehmi.log 2>&1 &
hpid=$!
sleep 8
echo "=== requesting home lifecycle READY(2), RUN(3) ==="
dbus-send --session --print-reply --dest=ccos.service.AppService /ccos/service/AppService ccos.service.AppService.RequestStateChange string:homehmi uint32:2
sleep 2
dbus-send --session --print-reply --dest=ccos.service.AppService /ccos/service/AppService ccos.service.AppService.RequestStateChange string:homehmi uint32:3
sleep 3
echo "=== showing HOME application ==="
dbus-send --session --print-reply --dest=ccos.service.AppService /ccos/service/AppService ccos.service.AppService.LaunchApp string:"{\"targetAppId\":\"homehmi\",\"sourceAppId\":\"qemu\",\"screenType\":8,\"appServiceId\":\"HOME\",\"appLayerIdType\":0,\"appLayerId\":\"APPLICATION\",\"userData\":{}}"
sleep 3
cat /tmp/homehmi.log
echo "=== service diagnostics ==="
for svc in shareddataservice memoryservice persistenceservice appservice userservice variantservice clockservice appeventmanager; do
    echo "--- $svc ---"
    tail -20 /tmp/$svc.log
done
echo "=== DLT diagnostics ==="
grep -E "ECU1 APPS|ECU1 HOME.*(HMI|HWND|QML|error|warn|HOME|ACOM)|createFd" /tmp/dlt-ascii.log | tail -140
echo "=== appservice introspection ==="
dbus-send --session --print-reply --dest=ccos.service.AppService /ccos/service/AppService org.freedesktop.DBus.Introspectable.Introspect
dbus-send --session --print-reply --dest=ccos.service.AppService /ccos/service/AppService ccos.service.AppService.serviceDump string:/tmp/appservice-dump
cat /tmp/appservice-dump
echo "=== app event API ==="
dbus-send --session --print-reply --dest=ccos.sys.appeventmanager.AppEventController /ccos/sys/appeventmanager/AppEventController org.freedesktop.DBus.Introspectable.Introspect
echo "=== registered session names ==="
dbus-send --session --print-reply --dest=org.freedesktop.DBus / org.freedesktop.DBus.ListNames
echo "=== processes ==="
ps | grep -E "weston|homehmi|dbus"
echo CCNC_CAPTURE_READY
sleep 8
kill "$hpid" "$wpid" 2>/dev/null
echo "=== final weston log ==="
cat /tmp/weston-hmi.log
echo "=== data logs ==="
find /ccos/data -name "*.log" | head -10
exit 0
'
