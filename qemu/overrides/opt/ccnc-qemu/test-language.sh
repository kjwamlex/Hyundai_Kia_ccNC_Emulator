#!/bin/sh
set -e
ccnc -ec '
test -f /run/ccnc-qemu/apps-ready
test -f /run/ccnc-qemu/settings-ready
for service in setupmanager language-state; do
    kill -0 "$(cat /run/ccnc-qemu/$service.pid)"
done
'
language() {
    ccnc -ec "export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/ccos_session_bus_socket; python3 /opt/ccnc-qemu/check-language.py $1"
}
# Use a new state disk for the first run; this also checks the first-boot fallback.
language 0
echo CCNC_LANG_SETTINGS
sleep 2
echo CCNC_LANG_GENERAL
sleep 2
echo CCNC_LANG_PAGE
sleep 2
echo CCNC_LANG_ENGLISH
# The original system-popup renderer now shows a timed language/VR notice.
# Allow it to expire before the next pointer selection.
sleep 6
language 1
echo CCNC_LANG_SHOT
sleep 1
echo CCNC_LANG_KOREAN
# The original system-popup renderer now shows a timed language/VR notice.
# Allow it to expire before the next pointer selection.
sleep 6
language 0
echo CCNC_LANG_ENGLISH_AGAIN
# The original system-popup renderer now shows a timed language/VR notice.
# Allow it to expire before the next pointer selection.
sleep 6
language 1
echo CCNC_LANG_HOME
sleep 2
ccnc -ec '
grep -q "setting.general.language, value: 1" /tmp/ccnc-qemu/dlt.log
grep -q "changed:en_US" /tmp/ccnc-qemu/dlt.log
python3 /opt/ccnc-qemu/window-dump.py --expect-window HOME.APPLICATION visible
cat /tmp/ccnc-qemu/language-state.log
'
echo CCNC_CAPTURE_READY
sleep 1
echo CCNC_LANGUAGE_SWITCHING_OK
