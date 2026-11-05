#!/bin/sh
set -e
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket
layer_type=2
case "${1:-}" in
    home) app=homehmi; service=HOME; scene=HOME.Main ;;
    media) app=mediahomehmi; service=MEDIAHOME; scene=MEDIAHOME.Main ;;
    phone) app=phonehmi; service=PHONE; scene=PHONE.Main ;;
    audio) app=audiohmi; service=AUDIO; scene=MEDIA_AUDIO; layer_type=1 ;;
    settings) app=setuphmi; service=SETUP; scene=SETUP_GATE; layer_type=1 ;;
    engineering)
        /opt/ccnc-qemu/start-engineering.sh
        app=engineeringmodehmi; service=ENGINEERINGMODE; scene=ENGMODE_MAIN; layer_type=1 ;;
    welcome|goodbye)
        unset LD_PRELOAD
        exec python3 /opt/ccnc-qemu/play-animation.py "$1" >>/tmp/ccnc-qemu/animation.log 2>&1 ;;
    tone) exec aplay -q -D default /opt/ccnc-qemu/audio-check.wav ;;
    *) exec python3 /opt/ccnc-qemu/app-launcher.py "$@" ;;
esac
python3 /opt/ccnc-qemu/app-launcher.py --ensure "$app"
dbus-send --session --print-reply --reply-timeout=5000 --dest=ccos.service.AppService /ccos/service/AppService ccos.service.AppService.LaunchApp \
    "string:{\"targetAppId\":\"$app\",\"sourceAppId\":\"qemu\",\"screenType\":8,\"appServiceId\":\"$service\",\"appLayerIdType\":$layer_type,\"appLayerId\":\"$scene\",\"userData\":{}}"
