#!/usr/bin/python3
"""Simulated power/hardwire/camera inputs and mounted USB adapter via OEM D-Bus APIs.

These are lab inputs, not observations of a vehicle. Package parsing and
cryptographic checks in the original updater are not replaced here.
"""
import os
from pathlib import Path
from gi.repository import Gio, GLib


def method(name, inputs, outputs):
    args = ''.join('<arg type="%s" direction="%s"/>' % (t, d)
                   for d, types in [('in', inputs), ('out', outputs)] for t in types)
    return '<method name="%s">%s</method>' % (name, args)


bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
registrations = []

# In the vehicle, lifecycle/vehicle services publish these sessions. Apps treat
# an absent restriction session as restricted. Match the lab's explicit parked,
# zero-speed inputs through the real NodeStateManager (Inactive=1).
system_bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
for session in ['SESSION_ITEM_RESTRICTION', 'RESTRICTION_NA']:
    for member in ['RegisterSession', 'SetSessionState']:
        result = system_bus.call_sync(
            'org.genivi.NodeStateManager', '/org/genivi/NodeStateManager/Consumer',
            'org.genivi.NodeStateManager.Consumer', member,
            GLib.Variant('(ssii)', (session, 'qemu', 1, 1)), GLib.VariantType('(i)'),
            Gio.DBusCallFlags.NONE, 5000, None).unpack()[0]
        if result != 1:  # NsmErrorStatus_Ok
            raise RuntimeError('%s %s failed: %d' % (member, session, result))
print('CCNC_LAB_RESTRICTION: parked simulation, restriction sessions inactive', flush=True)


def register(name, path, methods, handler):
    xml = '<node><interface name="%s">%s</interface></node>' % (name, ''.join(methods))
    node = Gio.DBusNodeInfo.new_for_xml(xml)

    def invoke(connection, sender, object_path, interface, member, params, invocation):
        try:
            signature, values = handler(member, params.unpack())
            invocation.return_value(GLib.Variant(signature, values))
        except (KeyError, ValueError) as error:
            invocation.return_dbus_error('org.ccnc.Qemu.Unsupported', str(error))

    registrations.append((node, invoke, bus.register_object(path, node.interfaces[0], invoke, None, None)))
    reply = bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                          'org.freedesktop.DBus', 'RequestName',
                          GLib.Variant('(su)', (name, 4)), GLib.VariantType('(u)'),
                          Gio.DBusCallFlags.NONE, 2000, None)
    if reply.unpack()[0] != 1:
        raise RuntimeError('D-Bus name already owned: ' + name)


def power(member, args):
    # Public POWER_NORMAL_ON=0, POWER_NORMAL_AV_ON=0. HAL enums differ.
    values = {'getPowerState': 0, 'getPowerNormalState': 0, 'getADMState': 0}
    if member in values:
        return '(ui)', (values[member], 0)
    if member in ['setEventListener', 'setNormalEventListener']:
        return '(i)', (0,)
    raise KeyError(member)


register('ccos.lifecycle.HLifeCyclePowerState', '/ccos/lifecycle/HLifeCyclePowerState',
         [method(m, [], ['u', 'i']) for m in ['getPowerState', 'getPowerNormalState', 'getADMState']] +
         [method(m, ['b'], ['i']) for m in ['setEventListener', 'setNormalEventListener']], power)


def hardwire(member, args):
    if member == 'getHardwireStatus':
        # ACC, IGN1, IGN3, parking brake and P gear are on. Speed is zero.
        event = args[0]
        if event not in [0, 1, 2, 4, 10, 11, 12, 13]:
            return '(ii)', (0, 13)  # Unavailable for unmodeled inputs.
        return '(ii)', (int(event in [0, 1, 2, 10, 11]), 0)
    if member in ['subscribeEvents', 'unsubscribeEvents']:
        if member == 'subscribeEvents':
            for event in args[0]:
                if event in [0, 1, 2, 4, 10, 11, 12, 13]:
                    GLib.idle_add(notify_hardwire, event)
        return '(i)', (0,)
    raise KeyError(member)


def notify_hardwire(event):
    bus.emit_signal(None, '/ccos/vehicle/extras/HHardwire',
                    'ccos.vehicle.extras.HHardwire', 'onHardwireStatusChanged',
                    GLib.Variant('(ii)', (event, int(event in [0, 1, 2, 10, 11]))))
    return False


register('ccos.vehicle.extras.HHardwire', '/ccos/vehicle/extras/HHardwire',
         [method('getHardwireStatus', ['i'], ['i', 'i'])] +
         [method(m, ['ai'], ['i']) for m in ['subscribeEvents', 'unsubscribeEvents']] +
         ['<signal name="onHardwireStatusChanged"><arg type="i"/><arg type="i"/></signal>'], hardwire)
# This image's HExteriorCamera API uses string listener tokens, not the
# boolean listener API used by the power service. No camera is active in QEMU.
# Report CAMERA_OFF=0 before appeventmanager initializes its shared mode state;
# otherwise its default MAX=9 makes the OEM popup manager hide update dialogs.
def camera(member, args):
    print('CCNC_LAB_CAMERA: %s %s' % (member, args), flush=True)
    if member == 'getAssistanceViewMode':
        return '(i)', (0,)
    if member == 'setEventListener':
        return '(s)', ('qemu-camera-off',)
    if member in ['subscribeEvents', 'unsubscribeEvents']:
        return '(si)', (args[1], 0)
    raise KeyError(member)


register('ccos.camera.HExteriorCameraFrontCenter', '/ccos/camera/HExteriorCameraFrontCenter', [
    method('getAssistanceViewMode', [], ['i']),
    method('setEventListener', ['s'], ['s']),
    method('subscribeEvents', ['ai', 's'], ['s', 'i']),
    method('unsubscribeEvents', ['ai', 's'], ['s', 'i']),
], camera)


# Adapter for the lab USB mount. Only real mounted image contents are exposed;
# the OEM scanner and update result signals remain in the original binaries.
USB_PATH = '/run/media/USB_Front'
DEVICE = 'ccos.device.DeviceManager'
DEVICE_PATH = '/ccos/device/DeviceManager'


def usb_mounted():
    return os.path.ismount(USB_PATH) and Path('/run/ccnc-qemu/usb-fstype').is_file()


def volume():
    if not usb_mounted():
        return (0, 0, [], '', '', '', '', 13)
    st = os.statvfs(USB_PATH)
    # OEM sizes are KiB, encoded as uint32.
    return (min(st.f_bavail * st.f_frsize // 1024, 0xffffffff),
            min(st.f_blocks * st.f_frsize // 1024, 0xffffffff), [1],
            Path('/run/ccnc-qemu/usb-fstype').read_text().strip(),
            'CCNC-LAB-USB', 'CCNC_LAB', USB_PATH, 0)


def device(member, args):
    print('CCNC_LAB_DEVICE: %s %s' % (member, args), flush=True)
    if member == 'getDeviceInfo':
        present = usb_mounted() and args == (1, 1)
        return '(ua{ss}i)', (3 if present else 2, {}, 0)
    if member == 'getDeviceInfos':
        present = usb_mounted() and args[0] in [0, 1] and args[1] in [0, 1]
        return '(a(ua{ss})i)', ([(3, {})] if present else [], 0)
    if member == 'getVolumeInfo':
        return '(uuaussssi)', volume() if args[0] == 1 else (0, 0, [], '', '', '', '', 13)
    if member == 'getVolumeInfoByPath':
        v = volume() if args[0] == USB_PATH else (0, 0, [], '', '', '', '', 13)
        return '(uuausssi)', v[:6] + (v[7],)
    if member == 'getTotalVolumeInfo':
        v = volume()
        return '(a(uusssssau)i)', ([(v[0], v[1], v[6], '/dev/sda', v[3], v[4], v[5], v[2])] if usb_mounted() else [], 0)
    if member in ['requestUnmount', 'requestUnmountSync']:
        return '(i)', (13,)  # Mount lifecycle is controlled by the lab launcher.
    raise KeyError(member)


register(DEVICE, DEVICE_PATH, [
    method('getDeviceInfo', ['u', 'u'], ['u', 'a{ss}', 'i']),
    method('getDeviceInfos', ['u', 'u'], ['a(ua{ss})', 'i']),
    method('getVolumeInfo', ['u'], ['u', 'u', 'au', 's', 's', 's', 's', 'i']),
    method('getVolumeInfoByPath', ['s'], ['u', 'u', 'au', 's', 's', 's', 'i']),
    method('getTotalVolumeInfo', [], ['a(uusssssau)', 'i']),
    method('requestUnmount', ['s'], ['i']),
    method('requestUnmountSync', ['s'], ['i']),
    '<signal name="deviceStatusUpdated"><arg type="u"/><arg type="u"/><arg type="u"/></signal>',
], device)

last_usb = None


def poll_usb():
    global last_usb
    mounted = usb_mounted()
    if mounted != last_usb:
        last_usb = mounted
        bus.emit_signal(None, DEVICE_PATH, DEVICE, 'deviceStatusUpdated',
                        GLib.Variant('(uuu)', (1, 3 if mounted else 2, 1)))
        print('CCNC_LAB_USB: ' + ('mounted read-only' if mounted else 'absent'), flush=True)
    return True


GLib.timeout_add_seconds(3, poll_usb)
print('CCNC_LAB_STATE_READY: simulated ignition on, parked, zero speed, camera off', flush=True)
GLib.MainLoop().run()
