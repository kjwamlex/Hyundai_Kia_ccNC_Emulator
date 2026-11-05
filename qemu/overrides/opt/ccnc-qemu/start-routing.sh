#!/bin/sh
# Original local SOME/IP router; external vehicle peers remain unavailable.
set -e
export VSOMEIP_APPLICATION_NAME=routingmanagerd
export VSOMEIP_CONFIGURATION=/ccos/daemons/routingmanagerd/vsomeip.json
python3 - <<'PY'
import json
from pathlib import Path
path = Path('/ccos/daemons/routingmanagerd/vsomeip.json')
config = json.loads(path.read_text())
config['unicast'] = '127.0.0.1'
config['service-discovery']['enable'] = 'false'
path.write_text(json.dumps(config))
PY
/ccos/daemons/routingmanagerd/routingmanagerd >/tmp/ccnc-qemu/routingmanagerd.log 2>&1 &
echo $! >/run/ccnc-qemu/routingmanagerd.pid
i=0
until [ -S /tmp/ccos/vsomeip-0 ]; do
    kill -0 "$(cat /run/ccnc-qemu/routingmanagerd.pid)"
    i=$((i+1))
    [ "$i" -lt 100 ] || { cat /tmp/ccnc-qemu/routingmanagerd.log; exit 1; }
    sleep 0.1
done
echo 'CCNC_ROUTING_READY: original SOME/IP router, guest-local transport'
