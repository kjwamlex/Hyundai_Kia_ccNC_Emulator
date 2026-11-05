#!/bin/sh
set -e
mode=${1:-desktop}
export XDG_RUNTIME_DIR=/run/user/0
export WAYLAND_DISPLAY=wayland-system
export HOME=/home/root
export QT_QPA_PLATFORM=wayland
export QT_QUICK_BACKEND=software
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1
export QML2_IMPORT_PATH=/ccos/apps/share/qml:/ccos/apps/share/plugins
export QT_PLUGIN_PATH=/ccos/apps/share/plugins:/usr/lib/plugins
export CCOS_IMAGE_PATH=/ccos/apps/share/images-2
export XDG_CACHE_HOME=/ccos/data/apps/.cache
mkdir -p "$XDG_RUNTIME_DIR" /run/ccnc-qemu /tmp/ccnc-qemu "$XDG_CACHE_HOME"
chmod 700 "$XDG_RUNTIME_DIR"
if [ "$mode" = desktop ]; then
    weston --no-config --backend=fbdev-backend.so --device=/dev/fb0 --tty=2 --shell=desktop-shell.so --socket="$WAYLAND_DISPLAY" --idle-time=0 --log=/tmp/ccnc-qemu/weston.log >/tmp/ccnc-qemu/weston-stdout.log 2>&1 &
    echo $! >/run/ccnc-qemu/weston.pid
    sleep 0.5
    weston-simple-shm >/tmp/ccnc-qemu/simple-shm.log 2>&1 &
    echo $! >/run/ccnc-qemu/client.pid
    echo 'CCNC_DESKTOP_STARTED: original Weston compositor and shared-memory client'
else
    export QT_WAYLAND_SHELL_INTEGRATION=ivi-shell
    export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket
    export LD_PRELOAD=/opt/ccnc-qemu/libashmem-qemu.so:/ccos/lib/libtrace.so
    mkdir -p /run/dbus /var/volatile/log /var/volatile/tmp /tmp/ccos /ccos/data/log/trace
    dbus-daemon --system --fork --nopidfile
    dbus-daemon --session --fork --address="$DBUS_SESSION_BUS_ADDRESS"
    cp /etc/dlt.conf /tmp/ccnc-qemu/dlt.conf
    printf '\nPrintASCII = 1\n' >>/tmp/ccnc-qemu/dlt.conf
    dlt-daemon -c /tmp/ccnc-qemu/dlt.conf 2>&1 | python3 /opt/ccnc-qemu/log-writer.py /tmp/ccnc-qemu/dlt.log &
    /usr/bin/NodeStateManager >/tmp/ccnc-qemu/nodestatemanager.log 2>&1 &
    echo $! >/run/ccnc-qemu/nodestatemanager.pid
    python3 -u /opt/ccnc-qemu/app-launcher.py --daemon >/tmp/ccnc-qemu/app-launcher.log 2>&1 &
    echo $! >/run/ccnc-qemu/app-launcher.pid
    i=0
    until grep -q CCNC_APP_LAUNCHER_READY /tmp/ccnc-qemu/app-launcher.log; do
        kill -0 "$(cat /run/ccnc-qemu/app-launcher.pid)"
        i=$((i+1))
        [ "$i" -lt 100 ] || { cat /tmp/ccnc-qemu/app-launcher.log; exit 1; }
        sleep 0.1
    done
    for svc in shareddataservice memoryservice persistenceservice iacservice appservice userservice variantservice clockservice systemservice; do
        (cd /ccos/services/$svc && exec ./$svc) >/tmp/ccnc-qemu/$svc.log 2>&1 &
        echo $! >/run/ccnc-qemu/$svc.pid
        sleep 1
    done
    python3 -u /opt/ccnc-qemu/language-state.py >/tmp/ccnc-qemu/language-state.log 2>&1 &
    echo $! >/run/ccnc-qemu/language-state.pid
    i=0
    until grep -q CCNC_LANGUAGE_READY /tmp/ccnc-qemu/language-state.log; do
        kill -0 "$(cat /run/ccnc-qemu/language-state.pid)"
        i=$((i+1))
        [ "$i" -lt 60 ] || { cat /tmp/ccnc-qemu/language-state.log; exit 1; }
        sleep 0.1
    done
    cat >/tmp/ccnc-qemu/weston.ini <<EOF
[core]
idle-time=0
shell=ivi-shell.so
modules=/ccos/lib/window-manager-service.so
[ccos]
window-manager-policy=/ccos/lib/window-manager-policy.so
EOF
    weston --config=/tmp/ccnc-qemu/weston.ini --backend=fbdev-backend.so --device=/dev/fb0 --tty=2 --socket="$WAYLAND_DISPLAY" --log=/tmp/ccnc-qemu/weston.log >/tmp/ccnc-qemu/weston-stdout.log 2>&1 &
    echo $! >/run/ccnc-qemu/weston.pid
    sleep 1
    python3 -u /opt/ccnc-qemu/lab-state.py >/tmp/ccnc-qemu/lab-state.log 2>&1 &
    echo $! >/run/ccnc-qemu/lab-state.pid
    i=0
    until grep -q CCNC_LAB_STATE_READY /tmp/ccnc-qemu/lab-state.log; do
        kill -0 "$(cat /run/ccnc-qemu/lab-state.pid)"
        i=$((i+1))
        [ "$i" -lt 40 ] || exit 1
        sleep 0.1
    done
    (cd /ccos/apps/manager/appeventmanager && export LD_PRELOAD=/opt/ccnc-qemu/libapp-launch-qemu.so:$LD_PRELOAD && exec ./appeventmanager) >/tmp/ccnc-qemu/appeventmanager.log 2>&1 &
    echo $! >/run/ccnc-qemu/appeventmanager.pid
    i=0
    until dbus-send --session --print-reply --reply-timeout=1000 --dest=ccos.sys.appeventmanager.AppLayerController /ccos/sys/appeventmanager/AppLayerController org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1; do
        i=$((i+1))
        if [ "$i" -ge 100 ]; then
            echo 'CCNC_HMI_ERROR: AppLayerController did not become ready'
            exit 1
        fi
        sleep 0.1
    done
    /opt/ccnc-qemu/start-routing.sh
    /opt/ccnc-qemu/start-media.sh
    (cd /ccos/apps/manager/mediagatemanager
        export VSOMEIP_APPLICATION_NAME=mediagatemanager
        export VSOMEIP_CONFIGURATION=/ccos/daemons/routingmanagerd/vsomeip.json
        export LD_PRELOAD=/opt/ccnc-qemu/libapp-launch-qemu.so:$LD_PRELOAD
        exec ./mediagatemanager) >/tmp/ccnc-qemu/mediagatemanager.log 2>&1 &
    echo $! >/run/ccnc-qemu/mediagatemanager.pid
    /opt/ccnc-qemu/run-app.sh homehmi >/tmp/ccnc-qemu/homehmi.log 2>&1 &
    echo $! >/run/ccnc-qemu/homehmi.pid
    /opt/ccnc-qemu/show-home.sh >/tmp/ccnc-qemu/show-home.log 2>&1 || {
        cat /tmp/ccnc-qemu/show-home.log /tmp/ccnc-qemu/homehmi.log
        exit 1
    }
    cat /tmp/ccnc-qemu/show-home.log
    /opt/ccnc-qemu/start-update.sh
    /opt/ccnc-qemu/start-settings.sh
    for app in popupmanager systempopuphmi splitscreenhmi statusbarhmi rfconnsetuphmi phonehmi audiohmi mediahomehmi vehicleupdatehmi updatehmi setuphmi; do
        /opt/ccnc-qemu/run-app.sh "$app" >/tmp/ccnc-qemu/$app.log 2>&1 &
        echo $! >/run/ccnc-qemu/$app.pid
        i=0
        until grep -q "CHANGED : $app - state: RUN" /tmp/ccnc-qemu/dlt.log; do
            if ! kill -0 "$(cat /run/ccnc-qemu/$app.pid)"; then
                echo "CCNC_HMI_ERROR: $app exited during initialization"
                cat /tmp/ccnc-qemu/$app.log
                tail -60 /tmp/ccnc-qemu/dlt.log
                exit 1
            fi
            i=$((i+1))
            if [ "$i" -ge 150 ]; then
                echo "CCNC_HMI_ERROR: $app did not become ready"
                exit 1
            fi
            sleep 0.2
        done
        cp /run/ccnc-qemu/$app.pid /run/ccnc-qemu/$app.ready
    done
    # statusbarhmi emits OEM Back/Menu keys through uinput. The vendor router
    # forwards these to the focused HMI through the compositor's hinput protocol.
    (cd /ccos/services/windowservice && exec ./window-input-router) >/tmp/ccnc-qemu/window-input-router.log 2>&1 &
    echo $! >/run/ccnc-qemu/window-input-router.pid
    i=0
    until grep 'WIR-.*device is added (statusbarhmi device)' /tmp/ccnc-qemu/dlt.log >/dev/null; do
        kill -0 "$(cat /run/ccnc-qemu/window-input-router.pid)"
        i=$((i+1))
        if [ "$i" -ge 150 ]; then
            echo 'CCNC_HMI_ERROR: navigation input router did not become ready'
            cat /tmp/ccnc-qemu/window-input-router.log
            exit 1
        fi
        sleep 0.2
    done
    python3 -u /opt/ccnc-qemu/key-bridge.py >/tmp/ccnc-qemu/keys.log 2>&1 &
    echo $! >/run/ccnc-qemu/keys.pid
    i=0
    until grep -q CCNC_KEYS_READY /tmp/ccnc-qemu/keys.log; do
        kill -0 "$(cat /run/ccnc-qemu/keys.pid)"
        i=$((i+1))
        if [ "$i" -ge 50 ]; then
            cat /tmp/ccnc-qemu/keys.log
            exit 1
        fi
        sleep 0.1
    done
    touch /run/ccnc-qemu/apps-ready
    echo 'CCNC_APPS_READY: Media, Phone, Audio and Settings preloaded; F1-F5 navigation, F6 welcome, F7 goodbye, F8 test tone, F9 engineering'
fi
