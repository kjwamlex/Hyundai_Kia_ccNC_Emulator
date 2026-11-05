#!/bin/sh
set -e
ccnc -ec '
test -c /dev/snd/pcmC0D0p
amixer -c 0 sset Master 70% unmute
aplay -D default /opt/ccnc-qemu/audio-check.wav
echo CCNC_AUDIO_PLAYBACK_OK
'
sleep 1
