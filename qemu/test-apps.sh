#!/bin/sh
set -e
ccnc -ec '
test -f /run/ccnc-qemu/apps-ready
for service in audioservice mediaservice mediagatemanager rfconnsetuphmi phonehmi audiohmi mediahomehmi keys; do
    kill -0 "$(cat /run/ccnc-qemu/$service.pid)"
done
i=0
until grep CCNC_KEYS_READY /tmp/ccnc-qemu/keys.log; do
    i=$((i+1))
    if [ "$i" -ge 30 ]; then cat /tmp/ccnc-qemu/keys.log; exit 1; fi
    sleep 0.1
done
'
wait_app() {
    app=$1
    i=0
    until ccnc -c "grep 'CHANGED : $app - state: RUN' /tmp/ccnc-qemu/dlt.log | tail -1 | grep -q 'running state: FOREGROUND'"; do
        i=$((i+1))
        if [ "$i" -ge 75 ]; then
            ccnc -c 'tail -40 /tmp/ccnc-qemu/keys.log; cat /tmp/ccnc-qemu/audiohmi.log; grep -E "ECU1 (AUDI|MS)|audiohmi" /tmp/ccnc-qemu/dlt.log | tail -90'
            echo "CCNC_APP_FAILED: $app"
            exit 1
        fi
        sleep 0.2
    done
    echo "CCNC_APP_FOREGROUND_OK: $app"
}
ccnc -ec '/opt/ccnc-qemu/open-app.sh tone; echo CCNC_AUDIO_PLAYBACK_OK'
echo CCNC_MEDIA_KEY_READY
wait_app mediahomehmi
sleep 2
echo CCNC_CAPTURE_READY
sleep 1
echo CCNC_PHONE_KEY_READY
wait_app phonehmi
echo CCNC_AUDIO_KEY_READY
wait_app audiohmi
echo CCNC_HOME_KEY_READY
wait_app homehmi
sleep 15
ccnc -ec '
for service in rfconnsetuphmi phonehmi audiohmi mediahomehmi mediagatemanager mediaservice; do
    if ! kill -0 "$(cat /run/ccnc-qemu/$service.pid)"; then
        echo "CCNC_PROCESS_FAILED: $service"
        cat /tmp/ccnc-qemu/$service.log
        grep -E "ECU1 (AUDI|MS)|ANR signal" /tmp/ccnc-qemu/dlt.log | tail -90
        exit 1
    fi
done
'
ccnc -ec '
kill -0 "$(cat /run/ccnc-qemu/audioservice.pid)"
! grep -q "ANR signal" /tmp/ccnc-qemu/audioservice.log
echo CCNC_AUDIO_POLICY_STABLE_OK
'
