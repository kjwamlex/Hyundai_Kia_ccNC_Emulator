#!/usr/bin/python3
"""Start OEM HMI processes on request, then let OEM AppService show the screen.

Only executables found in the firmware's app directories are eligible. Metadata
comes from those same directories; intents and vehicle/backend results are not
fabricated. The socket stays inside the guest, mode 0600.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import socketserver
import subprocess
import threading
import time

ROOT = Path('/opt/ccnc-qemu')
RUN = Path('/run/ccnc-qemu')
LOG = Path('/tmp/ccnc-qemu')
SOCKET = str(RUN / 'app-launcher.sock')
ALIASES = {'home': 'homehmi', 'media': 'mediahomehmi', 'phone': 'phonehmi',
           'audio': 'audiohmi', 'settings': 'setuphmi', 'engineering': 'engineeringmodehmi',
           'projection': 'phoneprojectionhmi', 'cinema': 'theaterhmi', 'radio': 'radiohmi'}
LOCK = threading.RLock()
CHILDREN = {}
DEPENDENCIES = {
    'theaterhmi': ['remotecontrolmanager'],
    'petcarehmi': ['remotecontrolmanager'],
    'streaminghmi': ['remotecontrolmanager', 'musicsearchmanager'],
    'usbvideohmi': ['remotecontrolmanager'],
    'webosprojectionhmi': ['remotecontrolmanager'],
    'engineeringmodehmi': ['engineeringmodemanager'],
}


def catalog():
    result = {}
    for path in sorted(Path('/ccos/apps').glob('*/*/appinfo.json')):
        try:
            info = json.loads(path.read_text())
            if (path.parent / path.parent.name).is_file():
                result[path.parent.name] = info
        except (OSError, ValueError):
            continue
    return result


def resolve(intent, apps):
    target = intent.get('targetAppId')
    if target:
        if target in apps:
            return target
        matches = [app for app, info in apps.items() if info['common'].get('appId') == target]
        if len(matches) == 1:
            return matches[0]
        raise ValueError('app is absent from executable catalog: ' + str(target))
    service = intent.get('appServiceId')
    matches = [app for app, info in apps.items() if service in info.get('appServices', {})]
    # Both North American radio packages register NARADIO. Use the standard one.
    if 'naradiohmi' in matches:
        return 'naradiohmi'
    if len(matches) != 1:
        raise ValueError('cannot resolve service: ' + str(service))
    return matches[0]


def alive(app):
    try:
        pid = int((RUN / (app + '.pid')).read_text())
        # kill(0) also succeeds for zombies and recycled PIDs.
        stat = Path('/proc/%d/stat' % pid).read_text().split()
        command = Path('/proc/%d/cmdline' % pid).read_bytes().split(b'\0')[0]
        return stat[2] != 'Z' and os.path.basename(os.fsdecode(command)) == app
    except (OSError, ValueError, IndexError):
        return False


def ready(app):
    if not alive(app):
        return False
    try:
        return (RUN / (app + '.ready')).read_text() == (RUN / (app + '.pid')).read_text()
    except OSError:
        return False


def start(app, apps):
    if ready(app):
        return
    if alive(app):
        raise RuntimeError(app + ' is alive but has not reached lifecycle RUN')
    old = CHILDREN.pop(app, None)
    if old is not None:
        old.poll()
    app_id = apps[app]['common'].get('appId', app)
    lifecycle = LOG / 'lifecycle' / app_id
    before = lifecycle.read_bytes() if lifecycle.exists() else b''
    with (LOG / (app + '.log')).open('w') as stream:
        process = subprocess.Popen([str(ROOT / 'run-app.sh'), app], stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    CHILDREN[app] = process
    (RUN / (app + '.pid')).write_text(str(process.pid) + '\n')
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('%s exited (%d); see %s.log' % (app, process.returncode, app))
        current = lifecycle.read_bytes() if lifecycle.exists() else b''
        if current != before and ('CHANGED : %s - state: RUN' % app_id).encode() in current:
            (RUN / (app + '.ready')).write_text(str(process.pid) + '\n')
            print('CCNC_APP_STARTED: ' + app, flush=True)
            return
        time.sleep(.1)
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    raise RuntimeError(app + ' lifecycle readiness timed out; see ' + app + '.log')


def ensure(intent, apps):
    with LOCK:
        app = resolve(intent, apps)
        for dependency in DEPENDENCIES.get(app, []):
            start(dependency, apps)
        start(app, apps)
        return app


def request(intent):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(40)
        connection.connect(SOCKET)
        connection.sendall((json.dumps(intent) + '\n').encode())
        reply = connection.makefile('rb').readline(4096).decode().strip()
    if not reply.startswith('0 '):
        raise RuntimeError(reply)
    return reply[2:]


def default_intent(app, apps, service=None, prefer_scene=False):
    app = ALIASES.get(app, app)
    info = apps[app]
    for name, data in info['appServices'].items():
        if service and service != name:
            continue
        windows = [w for w in data.get('windows', []) if w.get('type') in ('APPLICATION', 'CLIMATE')]
        if not windows:
            continue
        intents = [i for i in data.get('intents', []) if 'FRONT_CENTER' in i.get('screens', [])]
        ids = [i for group in intents for i in group['ids'] if i not in ('KEY_EVENT', 'SPLIT_HANDLER')]
        scene = next((sid for key in windows[0].get('sceneSetKeys', [])
                      for sid in data.get('sceneSets', {}).get(key, {}).get('ids', [])), None)
        if not ids and not scene:
            continue
        if prefer_scene and scene:
            ids = []
        # Match OEM intents when available; direct scene selection otherwise.
        return dict(targetAppId=info['common'].get('appId', app), sourceAppId='qemu', screenType=8, appServiceId=name,
                    appLayerIdType=1 if ids else 2, appLayerId=ids[0] if ids else scene, userData={})
    raise ValueError(app + ' has no front application window (support/overlay app)')


def launch(intent):
    request(intent)
    env = dict(os.environ, DBUS_SESSION_BUS_ADDRESS='unix:path=/run/dbus/ccos_session_bus_socket')
    subprocess.run(['dbus-send', '--session', '--print-reply', '--reply-timeout=5000',
                    '--dest=ccos.service.AppService', '/ccos/service/AppService',
                    'ccos.service.AppService.LaunchApp', 'string:' + json.dumps(intent)],
                   env=env, check=True)


def daemon():
    apps = catalog()
    # Replace the missing systemd activation with our explicit process startup.
    for app, info in apps.items():
        if info['common'].get('loadingType') == 'ondemand':
            info['common']['loadingType'] = 'preloaded'
            path = next(Path('/ccos/apps').glob('*/' + app + '/appinfo.json'))
            path.write_text(json.dumps(info))

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.connection.settimeout(45)
            try:
                data = self.rfile.readline(65537)
                if len(data) > 65536 or not data.endswith(b'\n'):
                    raise ValueError('invalid request size')
                intent = json.loads(data)
                app = ensure(intent, apps)
                response = '0 ' + app
            except Exception as error:
                response = '1 ' + str(error)
                print('CCNC_APP_FAILED: ' + response, flush=True)
            self.wfile.write((response.replace('\n', ' ') + '\n').encode())

    class Server(socketserver.ThreadingUnixStreamServer):
        daemon_threads = True

    RUN.mkdir(parents=True, exist_ok=True)
    Path(SOCKET).unlink(missing_ok=True)
    with Server(SOCKET, Handler) as server:
        os.chmod(SOCKET, 0o600)
        print('CCNC_APP_LAUNCHER_READY: %d executable apps' % len(apps), flush=True)
        server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', nargs='?')
    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--ensure', action='store_true')
    parser.add_argument('--service')
    parser.add_argument('--scene', action='store_true', help='Use the first registered front scene instead of its intent')
    args = parser.parse_args()
    if args.daemon:
        daemon()
    elif args.list:
        for name in catalog():
            print(name)
    elif args.app:
        app = ALIASES.get(args.app, args.app)
        if args.ensure:
            print(request({'targetAppId': app}))
        else:
            launch(default_intent(app, catalog(), args.service, args.scene))
    else:
        parser.error('specify an app, --list or --daemon')
