#!/usr/bin/env python3
"""Call the original firmware's public HAudioController API for lab controls.
Signatures, the 16-byte opaque volume parameter, and enum values match 2.6.17.
"""
import ctypes as C
import sys
import time

lib = C.CDLL("libhaudio.so.2", mode=C.RTLD_GLOBAL)
def bind(name, result, *args):
    fn = getattr(lib, name)
    fn.restype, fn.argtypes = result, args
    return fn
integer = C.POINTER(C.c_int)
get = bind("_ZN4ccos5audio16HAudioController11getInstanceEv", C.c_void_p)
convert = bind("_ZN4ccos5audio19convertToHAudioTypeE10ZoneDevice9AudioZone", C.c_int, C.c_int, C.c_int)
controller = get()
device = C.c_int(convert(101, 2))  # OUT_SPEAKER, FRONT
command = sys.argv[1] if len(sys.argv)>1 else ""
if command == "volume":
    volume = int(sys.argv[2])
    if not 0 <= volume <= 45:
        raise SystemExit("volume range is 0..45")
    storage = (C.c_uint64 * 2)()
    ctor = bind("_ZN4ccos5audio17HAudioVolumeParamC1ERKNS0_16HAudioVolumeTypeERKNS0_16HAudioDeviceTypeERKjRKb", None, C.c_void_p, integer, integer, C.POINTER(C.c_uint), C.POINTER(C.c_bool))
    ctor(storage, C.byref(C.c_int(88)), C.byref(device), C.byref(C.c_uint(volume)), C.byref(C.c_bool(False)))
    fn = bind("_ZN4ccos5audio16HAudioController9setVolumeERKNS0_17HAudioVolumeParamE", C.c_int, C.c_void_p, C.c_void_p)
    result = fn(controller, storage)
    bind("_ZN4ccos5audio17HAudioVolumeParamD1Ev", None, C.c_void_p)(storage)
elif command in ("mute", "unmute"):
    fn = bind("_ZN4ccos5audio16HAudioController7setMuteERKNS0_14HAudioMuteTypeERKNS0_16HAudioDeviceTypeERKb", C.c_int, C.c_void_p, integer, integer, C.POINTER(C.c_bool))
    result = fn(controller, C.byref(C.c_int(0)), C.byref(device), C.byref(C.c_bool(command=="mute")))
elif command == "beep":
    fn = bind("_ZN4ccos5audio16HAudioController7setPlayERKNS0_15HAudioSoundTypeERKNS0_16HAudioDeviceTypeE", C.c_int, C.c_void_p, integer, integer)
    result = fn(controller, C.byref(C.c_int(0)), C.byref(device))
else:
    raise SystemExit("Usage: audio-control.py volume 0..45 | mute | unmute | beep")
time.sleep(0.3)
print("CCNC_AUDIO_CONTROL:", command, "result=", result, flush=True)
raise SystemExit(0 if result==0 else 1)
