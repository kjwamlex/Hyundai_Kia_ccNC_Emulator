#!/bin/sh
# Supply the minimal lab lifecycle state normally supplied by the head unit.
set -e
wait_log() {
    pattern=$1
    i=0
    until grep -q "$pattern" /tmp/ccnc-qemu/dlt.log; do
        kill -0 "$(cat /run/ccnc-qemu/homehmi.pid)"
        i=$((i+1))
        if [ "$i" -ge 150 ]; then
            echo "CCNC_HMI_ERROR: timed out waiting for $pattern"
            exit 1
        fi
        sleep 0.2
    done
}
wait_log 'homehmi - state: RUN'
dbus-send --session --print-reply --reply-timeout=5000 --dest=ccos.account.user.HUserProfile /ccos/account/user/HUserProfile ccos.account.user.HUserProfile.setActiveUser string:0
dbus-send --system --print-reply --reply-timeout=5000 --dest=org.genivi.NodeStateManager /org/genivi/NodeStateManager/Consumer org.genivi.NodeStateManager.Consumer.RegisterSession string:SESSION_ITEM_BOOTCOMPLETE string:qemu int32:1 int32:2
dbus-send --system --print-reply --reply-timeout=5000 --dest=org.genivi.NodeStateManager /org/genivi/NodeStateManager/Consumer org.genivi.NodeStateManager.Consumer.SetSessionState string:SESSION_ITEM_BOOTCOMPLETE string:qemu int32:1 int32:2
sleep 1
dbus-send --session --print-reply --reply-timeout=5000 --dest=ccos.service.AppService /ccos/service/AppService ccos.service.AppService.LaunchApp 'string:{"targetAppId":"homehmi","sourceAppId":"qemu","screenType":8,"appServiceId":"HOME","appLayerIdType":2,"appLayerId":"HOME.Main","userData":{}}'
wait_log 'HomeFrontWindow: onVisible()'
cp /run/ccnc-qemu/homehmi.pid /run/ccnc-qemu/homehmi.ready
touch /run/ccnc-qemu/home-ready
echo 'CCNC_HMI_READY: original homehmi foreground; guest 0; saved system language; simulated boot completion'
