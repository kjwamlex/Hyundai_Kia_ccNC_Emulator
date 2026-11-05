#!/bin/sh
ccnc -c '
export XDG_RUNTIME_DIR=/run/user/0 WAYLAND_DISPLAY=wayland-system
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket
sleep 8
echo "=== lifecycle ==="
echo "=== users ==="
dbus-send --session --print-reply --dest=ccos.account.user.HUserProfile /ccos/account/user/HUserProfile org.freedesktop.DBus.Introspectable.Introspect
dbus-send --session --print-reply --dest=ccos.account.user.HUserProfile /ccos/account/user/HUserProfile ccos.account.user.HUserProfile.getUserList
dbus-send --session --print-reply --dest=ccos.account.user.HUserProfile /ccos/account/user/HUserProfile ccos.account.user.HUserProfile.setActiveUser string:0
dbus-send --session --print-reply --dest=ccos.account.user.HUserProfile /ccos/account/user/HUserProfile ccos.account.user.HUserProfile.getActiveUser
echo "=== system ==="
dbus-send --session --print-reply --dest=ccos.system.HSystem /ccos/system/HSystem org.freedesktop.DBus.Introspectable.Introspect
dbus-send --session --print-reply --dest=ccos.system.HSystem /ccos/system/HSystem ccos.system.HSystem.setLanguageType int32:0
dbus-send --system --print-reply --dest=org.genivi.NodeStateManager /org/genivi/NodeStateManager/Consumer org.freedesktop.DBus.Introspectable.Introspect
cat /tmp/ccnc-qemu/nodestatemanager.log
dbus-send --system --print-reply --dest=org.genivi.NodeStateManager /org/genivi/NodeStateManager/Consumer org.genivi.NodeStateManager.Consumer.RegisterSession string:SESSION_ITEM_BOOTCOMPLETE string:qemu int32:1 int32:2
dbus-send --system --print-reply --dest=org.genivi.NodeStateManager /org/genivi/NodeStateManager/Consumer org.genivi.NodeStateManager.Consumer.SetSessionState string:SESSION_ITEM_BOOTCOMPLETE string:qemu int32:1 int32:2
dbus-send --system --print-reply --dest=org.genivi.NodeStateManager /org/genivi/NodeStateManager/Consumer org.genivi.NodeStateManager.Consumer.GetSessionState string:SESSION_ITEM_BOOTCOMPLETE int32:1
sleep 1
echo "=== app layer controller ==="
dbus-send --session --print-reply --dest=ccos.sys.appeventmanager.AppLayerController /ccos/sys/appeventmanager/AppLayerController org.freedesktop.DBus.Introspectable.Introspect
echo "=== launching HOME ==="
dbus-send --session --print-reply --dest=ccos.service.AppService /ccos/service/AppService ccos.service.AppService.LaunchApp string:"{\"targetAppId\":\"homehmi\",\"sourceAppId\":\"qemu\",\"screenType\":8,\"appServiceId\":\"HOME\",\"appLayerIdType\":2,\"appLayerId\":\"HOME.Main\",\"userData\":{}}"
sleep 5
echo "=== compositor ==="
cat /tmp/ccnc-qemu/weston.log /tmp/ccnc-qemu/weston-stdout.log
echo "=== home ==="
cat /tmp/ccnc-qemu/homehmi.log
echo "=== DLT ==="
grep -E "ECU1 (HOME|APPS|aem)" /tmp/ccnc-qemu/dlt.log | grep -v "HUnixSocketClient::connectToService" | tail -650
echo "=== manager ==="
cat /tmp/ccnc-qemu/appeventmanager.log
echo "=== image file access ==="
true
echo "=== proc ==="
ps
'
echo CCNC_CAPTURE_READY
sleep 2
exit 0
