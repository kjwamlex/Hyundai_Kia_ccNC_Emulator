#!/bin/sh
set -e
# Keep OEM routing/focus policy, replacing the physical DSP HAL in RAM only.
cp /opt/ccnc-qemu/libaudiohal-qemu.so /ccos/lib/libaudiohal.mobis.mst6g.so
python3 - <<'PY'
import json
from pathlib import Path
path = Path('/ccos/services/audioservice/audio_config.json')
config = json.loads(path.read_text())
config['modules'] = ['audiohal']
path.write_text(json.dumps(config))
PY
if [ -c /dev/snd/controlC0 ]; then
    amixer -c 0 sset Master 100% unmute >/tmp/ccnc-qemu/mixer.log 2>&1
fi
(cd /ccos/services/audioservice
    export LD_PRELOAD=/opt/ccnc-qemu/libaudio-platform-qemu.so:$LD_PRELOAD
    exec ./audioservice) >/tmp/ccnc-qemu/audioservice.log 2>&1 &
echo $! >/run/ccnc-qemu/audioservice.pid
i=0
until [ -S /tmp/ccos.audio.settings ]; do
    kill -0 "$(cat /run/ccnc-qemu/audioservice.pid)"
    i=$((i+1))
    if [ "$i" -ge 100 ]; then
        echo 'CCNC_MEDIA_ERROR: audio policy IPC did not start'
        exit 1
    fi
    sleep 0.1
done
# Exclude NVIDIA plugins from discovery, preserving the vendor plugin files.
mkdir -p /tmp/ccnc-qemu/gst-plugins /ccos/data/services/mediaservice/data
for plugin in /usr/lib/gstreamer-1.0/*.so; do
    case "${plugin##*/}" in
        libgstnv*|libgsthnv*|libgstsecnvm*|libgstopengl*|libgstvulkan*|libgsthvideo*) continue ;;
    esac
    ln -s "$plugin" /tmp/ccnc-qemu/gst-plugins/
done
export GST_PLUGIN_SYSTEM_PATH_1_0=/tmp/ccnc-qemu/gst-plugins
export GST_REGISTRY_1_0=/tmp/ccnc-qemu/gst-registry.bin
(cd /ccos/services/mediaservice && exec ./mediaservice) >/tmp/ccnc-qemu/mediaservice.log 2>&1 &
echo $! >/run/ccnc-qemu/mediaservice.pid
echo 'CCNC_AUDIO_POLICY_STARTED: QEMU output HAL; OEM route/focus policy, ALSA HDA playback'
