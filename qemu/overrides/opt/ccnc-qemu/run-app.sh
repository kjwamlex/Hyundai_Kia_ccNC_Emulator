#!/bin/sh
set -e
app=$1
case "$app" in ''|*[!a-z0-9_-]*) echo 'Invalid HMI app name' >&2; exit 1 ;; esac
export XDG_RUNTIME_DIR=/run/user/0 WAYLAND_DISPLAY=wayland-system HOME=/home/root
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket
export QT_QPA_PLATFORM=wayland QT_WAYLAND_SHELL_INTEGRATION=ivi-shell
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1
export VSOMEIP_APPLICATION_NAME=$app
export VSOMEIP_CONFIGURATION=/ccos/daemons/routingmanagerd/vsomeip.json
export QML2_IMPORT_PATH=/ccos/apps/hmi/$app/qml:/ccos/apps/share/qml:/ccos/apps/share/plugins
export QT_PLUGIN_PATH=/ccos/apps/share/plugins:/usr/lib/plugins
export CCOS_IMAGE_PATH=/ccos/apps/share/images-2
export XDG_CACHE_HOME=/ccos/data/apps/.cache
export LD_PRELOAD=/opt/ccnc-qemu/libmedia-platform-qemu.so:/opt/ccnc-qemu/libapp-launch-qemu.so:/opt/ccnc-qemu/libashmem-qemu.so:/ccos/lib/libtrace.so
if [ "$app" = engineeringmodehmi ]; then
    export LD_PRELOAD=/opt/ccnc-qemu/libengineering-platform-qemu.so:$LD_PRELOAD
fi
if [ "$app" = setuphmi ] && [ ! -f /run/ccnc-qemu/update-ready ]; then
    export LD_PRELOAD=/opt/ccnc-qemu/libsettings-platform-qemu.so:$LD_PRELOAD
fi
if [ "$app" = updatehmi ] || [ "$app" = vehicleupdatehmi ]; then
    export VSOMEIP_APPLICATION_NAME=$app
    export VSOMEIP_CONFIGURATION=/ccos/daemons/routingmanagerd/vsomeip.json
fi
export LD_LIBRARY_PATH=/opt/ccnc-qemu/mesa/lib
export QT_QUICK_BACKEND=rhi QSG_RHI_BACKEND=opengl QT_OPENGL=software
# Serialize OEM surface changes with rendering under the software compositor.
export QSG_RENDER_LOOP=basic
export LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe
export LIBGL_DRIVERS_PATH=/opt/ccnc-qemu/mesa/lib/dri
export __EGL_VENDOR_LIBRARY_FILENAMES=/opt/ccnc-qemu/mesa/egl.json
case "$app" in
    *) if [ -x "/ccos/apps/hmi/$app/$app" ]; then
           cd "/ccos/apps/hmi/$app"
       else
           cd "/ccos/apps/manager/$app"
       fi ;;
esac
exec "./$app"
