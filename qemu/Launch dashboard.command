#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
exec python3 qemu/run.py --gui ccnc --state
