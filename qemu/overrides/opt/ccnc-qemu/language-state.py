#!/usr/bin/python3
"""Restore/save guest-0 language while the lab omits the vendor boot graph.

The original setupmanager/HSystem APIs still apply changes and notify apps.
HSystem's shared variable is volatile; retain its valid value on the writable
guest filesystem so --state also retains the language across QEMU boots.
"""
import json
import os
from pathlib import Path
from gi.repository import Gio, GLib

BUS_NAME = 'ccos.system.HSystem'
OBJECT_PATH = '/ccos/system/HSystem'
STATE = Path('/ccos/data/ccnc-qemu/guest-0-language.json')
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)


def valid(value):
    # HLanguageType::MAX is 51 in this firmware. Korean=0, English (US)=1.
    return type(value) is int and 0 <= value < 51


def save(value):
    if not valid(value):
        return
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump({'language_type': value}, stream)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(STATE)
    print('CCNC_LANGUAGE_SAVED: type=%d' % value, flush=True)


def changed(connection, sender, path, interface, signal, params):
    save(params.unpack()[0])


bus.signal_subscribe(BUS_NAME, BUS_NAME, 'onLanguageChanged', OBJECT_PATH,
                     None, Gio.DBusSignalFlags.NONE, changed)
# The OEM service sends changes only to clients registered on this API.
bus.call_sync(BUS_NAME, OBJECT_PATH, BUS_NAME, 'setEventListener',
              GLib.Variant('(b)', (True,)), GLib.VariantType('()'),
              Gio.DBusCallFlags.NONE, 5000, None)
language, result = bus.call_sync(BUS_NAME, OBJECT_PATH, BUS_NAME, 'getLanguageType',
                               None, GLib.VariantType('(ii)'),
                               Gio.DBusCallFlags.NONE, 5000, None).unpack()
restored = False
if result != 0 or not valid(language):
    # A first boot has MAX/error because hardware/profile boot inputs are absent.
    language = 0
    if STATE.exists():
        saved = json.loads(STATE.read_text())['language_type']
        if not valid(saved):
            raise ValueError('Invalid saved HLanguageType')
        language = saved
    result, = bus.call_sync(BUS_NAME, OBJECT_PATH, BUS_NAME, 'setLanguageType',
                           GLib.Variant('(i)', (language,)), GLib.VariantType('(i)'),
                           Gio.DBusCallFlags.NONE, 5000, None).unpack()
    if result != 0:
        raise RuntimeError('HSystem rejected language: %d' % result)
    restored = True
save(language)
print('CCNC_LANGUAGE_READY: type=%d restored=%s' % (language, restored), flush=True)
GLib.MainLoop().run()
