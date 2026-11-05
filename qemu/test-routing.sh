#!/bin/sh
# Host: --gui ccnc --routing-test --audio wav --audio-file ... --screenshot ...
set -e
trap 'ccnc -c '\''tail -40 /tmp/ccnc-qemu/audioservice.log; tail -30 /tmp/ccnc-qemu/mediaservice.log; grep -Ei "NATURE|createPipeline|obtainMediaPlayer|setURL|VideoSink" /tmp/ccnc-qemu/dlt.log | tail -65'\''' EXIT
wait_log() {
    pattern=$1
    i=0
    until ccnc -c "grep -q '$pattern' /tmp/ccnc-qemu/dlt.log"; do
        i=$((i+1))
        if [ "$i" -ge 60 ]; then echo "CCNC_ROUTING_FAILED: $pattern"; exit 1; fi
        sleep 0.2
    done
    sleep 1
}
ccnc -ec 'test -f /run/ccnc-qemu/apps-ready'
echo CCNC_SETTINGS_KEY_READY
wait_log 'CHANGED : setuphmi - state: RUN, running state: FOREGROUND'
echo CCNC_SHOT_gate
echo CCNC_SETTINGS_SOUND_CLICK
wait_log 'setCurrentScene(): sceneId: SETUP.Sound.Main'
echo CCNC_SHOT_sound
echo CCNC_SETTINGS_GATE_AGAIN
sleep 1
echo CCNC_SETTINGS_GENERAL_CLICK
wait_log 'setCurrentScene(): sceneId: SETUP.General.Main'
echo CCNC_SHOT_general
echo CCNC_ROUTE_AUDIO_READY
wait_log 'CHANGED : audiohmi - state: RUN, running state: FOREGROUND'
echo CCNC_ROUTE_NATURE_CLICK
sleep 4
echo CCNC_SHOT_nature
ccnc -ec '
kill -0 "$(cat /run/ccnc-qemu/audioservice.pid)"
grep "QEMU_HAL_CONFIG qemu_media channels=2 format=2 rate=48000" /tmp/ccnc-qemu/audioservice.log
/opt/ccnc-qemu/audio-control.py volume 30
'
sleep 1
echo CCNC_PCM_high_start
sleep 3
echo CCNC_PCM_high_end
ccnc -ec '/opt/ccnc-qemu/audio-control.py mute'
sleep 1
echo CCNC_PCM_mute_start
sleep 3
echo CCNC_PCM_mute_end
ccnc -ec '/opt/ccnc-qemu/audio-control.py unmute'
sleep 1
echo CCNC_PCM_resume_start
sleep 3
echo CCNC_PCM_resume_end
ccnc -ec '/opt/ccnc-qemu/audio-control.py volume 20; /opt/ccnc-qemu/audio-control.py beep'
sleep 1
ccnc -ec '
for app in audioservice mediaservice mediagatemanager homehmi setuphmi audiohmi phonehmi mediahomehmi; do
    kill -0 "$(cat /run/ccnc-qemu/$app.pid)"
done
grep "QEMU_HAL_SOUND" /tmp/ccnc-qemu/audioservice.log
tail -28 /tmp/ccnc-qemu/audioservice.log
! grep -q "ANR signal" /tmp/ccnc-qemu/audioservice.log
echo CCNC_ROUTING_SETTINGS_OK
'
echo CCNC_CAPTURE_READY
sleep 1
