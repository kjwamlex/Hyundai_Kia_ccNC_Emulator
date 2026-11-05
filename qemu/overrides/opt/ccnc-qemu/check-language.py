#!/usr/bin/python3
"""Check the original service value and the lab's persisted boot value."""
import json
import sys
from pathlib import Path
from gi.repository import Gio, GLib

expected = int(sys.argv[1])
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
actual = bus.call_sync('ccos.system.HSystem', '/ccos/system/HSystem',
                       'ccos.system.HSystem', 'getLanguageType', None,
                       GLib.VariantType('(ii)'), Gio.DBusCallFlags.NONE, 3000, None).unpack()
assert actual == (expected, 0), actual
saved = json.loads(Path('/ccos/data/ccnc-qemu/guest-0-language.json').read_text())
assert saved['language_type'] == expected, saved
print('CCNC_LANGUAGE_OK: type=%d' % expected)
