#!/bin/sh
set -eu
wait_animation() {
    i=0
    until grep -q "$1" /ccnc/tmp/ccnc-qemu/animation.log 2>/dev/null; do
        if grep -q CCNC_ANIMATION_ERROR /ccnc/tmp/ccnc-qemu/animation.log 2>/dev/null; then
            head -c 12000 /ccnc/tmp/ccnc-qemu/animation.log
            exit 1
        fi
        i=$((i+1))
        if [ "$i" -gt 300 ]; then
            head -c 12000 /ccnc/tmp/ccnc-qemu/animation.log
            ccnc -c 'ps -eo pid,stat,comm,args | grep -E "animation|ffmpeg|aplay|weston"'
            echo 'CCNC_ANIMATION_TEST_TIMEOUT'
            exit 1
        fi
        sleep 0.1
    done
}
ccnc -ec 'test -f /run/ccnc-qemu/home-ready; grep -q "F6 welcome, F7 goodbye" /tmp/ccnc-qemu/keys.log'
# Supply a known sound in this test only, preserving any user-selected sound.
created_sound=0
if [ ! -e /ccnc/ccos/data/qemu/welcome.wav ]; then
    mkdir -p /ccnc/ccos/data/qemu
    cp /ccnc/opt/ccnc-qemu/audio-check.wav /ccnc/ccos/data/qemu/welcome.wav
    created_sound=1
fi
cleanup() {
    [ "$created_sound" -eq 0 ] || rm -f /ccnc/ccos/data/qemu/welcome.wav
}
trap cleanup EXIT
echo CCNC_CAPTURE_READY
sleep 1
for kind in welcome goodbye; do
    if [ "$kind" = welcome ]; then echo CCNC_WELCOME_KEY_READY; else echo CCNC_GOODBYE_KEY_READY; fi
    wait_animation "CCNC_ANIMATION_VISIBLE: $kind"
    echo "CCNC_SHOT_$kind"
    wait_animation "CCNC_ANIMATION_DONE: $kind"
    ccnc -ec 'kill -0 "$(cat /run/ccnc-qemu/weston.pid)"; ! grep -q "State:.*T" /proc/$(cat /run/ccnc-qemu/weston.pid)/status'
done
grep -q CCNC_ANIMATION_BUSY /ccnc/tmp/ccnc-qemu/animation.log
sleep 0.5
echo CCNC_SHOT_restored
sleep 0.5
cat /ccnc/tmp/ccnc-qemu/animation.log
echo CCNC_ANIMATION_KEYS_OK
