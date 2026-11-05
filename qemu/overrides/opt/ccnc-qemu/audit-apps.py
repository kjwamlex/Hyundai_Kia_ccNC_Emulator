#!/usr/bin/python3
"""Sequential startup/foreground audit. Run only in a disposable lab VM.

Emits JSON records and screenshot markers for the host. Stops audit-started
processes between tests so mutually exclusive regional apps can be inspected.
Foreground requires OEM lifecycle and a visible compositor window; physical
hardware functionality is not implied.
"""
import json
from pathlib import Path
import re
import signal
import sys
import time
import importlib.util
spec = importlib.util.spec_from_file_location('launcher', '/opt/ccnc-qemu/app-launcher.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

apps = launcher.catalog()
# Never stop the base GUI or services while auditing optional apps.
pinned = {path.stem for path in launcher.RUN.glob('*.pid') if launcher.alive(path.stem)}
scene_mode = '--scenes' in sys.argv
selected = [arg for arg in sys.argv[1:] if arg != '--scenes'] or sorted(path.name for path in Path('/ccos/apps/hmi').iterdir() if path.is_dir())
results = []
for app in selected:
    row = {'app': app, 'launch_mode': 'scene' if scene_mode else 'intent'}
    start = time.monotonic()
    offset = (launcher.LOG / 'dlt.log').stat().st_size
    try:
        if app not in apps:
            row['status'] = 'no-executable-metadata'
            continue
        try:
            intent = launcher.default_intent(app, apps, prefer_scene=scene_mode)
        except ValueError:
            intent = None
        row['intent'] = intent
        launcher.request({'targetAppId': app})
        row['process_ready'] = True
        if intent:
            launcher.launch(intent)
            time.sleep(2)
        else:
            time.sleep(.3)
        with (launcher.LOG / 'dlt.log').open('rb') as stream:
            stream.seek(offset)
            events = stream.read().decode(errors='replace')
        app_id = apps[app]['common'].get('appId', app)
        states = re.findall(r'CHANGED : ' + re.escape(app_id) + r' - state: RUN, running state: (\w+)', (launcher.LOG / 'dlt.log').read_text(errors='replace'))
        row['running_state'] = states[-1] if states else None
        row['alive'] = launcher.alive(app)
        dump = launcher.subprocess.run(['python3', str(launcher.ROOT / 'window-dump.py')],
                                      stdout=launcher.subprocess.PIPE,
                                      stderr=launcher.subprocess.PIPE, timeout=6)
        if dump.returncode == 0:
            windows = json.loads(dump.stdout)[0]['windows']
            services = set(apps[app].get('appServices', {}))
            row['visible_windows'] = [key['name'] for key, value in windows
                                      if key['name'].split('.')[0] in services
                                      and value.get('visibility') and value.get('displayed')
                                      and value.get('surfaceId') and value.get('opacity') == 1.0]
        else:
            row['window_probe_error'] = dump.stderr.decode(errors='replace')[-500:]

        row['status'] = ('foreground' if row['alive'] and row['running_state'] == 'FOREGROUND' and row.get('visible_windows') else
                         'support-ready' if row['alive'] and intent is None else
                         'ready-no-foreground' if row['alive'] else 'exited-after-launch')
        pid = (launcher.RUN / (app + '.pid')).read_text().strip()
        diagnostics = [line for line in events.splitlines() if ('[[' + pid + ':') in line and
                       any(text in line for text in ('Error:', 'is not installed', 'is not a type', 'can not show', 'failed to load'))]
        row['diagnostics'] = diagnostics[-8:]
        if row['status'] == 'ready-no-foreground':
            row['launch_events'] = [line for line in events.splitlines() if ('[[' + pid + ':') in line and any(term in line for term in ('onRequestShow', 'Intent', 'intent', 'onShow', 'onRun', 'isReady', 'not support', 'not available', 'Error'))][-15:]
        if not row['alive']:
            row['log_tail'] = (launcher.LOG / (app + '.log')).read_text(errors='replace')[-3500:]
        if intent:
            print('CCNC_APP_SHOT:' + app, flush=True)
            time.sleep(1)
    except Exception as error:
        row['status'] = 'startup-failed'
        row['error'] = str(error)
        path = launcher.LOG / (app + '.log')
        if path.exists():
            row['log_tail'] = path.read_text(errors='replace')[-2500:]
    finally:
        row['seconds'] = round(time.monotonic() - start, 2)
        results.append(row)
        print('CCNC_APP_RESULT:' + json.dumps(row, separators=(',', ':')), flush=True)
        (launcher.LOG / 'app-audit.json').write_text(json.dumps(results, indent=2))
        try:
            launcher.launch(launcher.default_intent('homehmi', apps))
            time.sleep(.2)
        except Exception as error:
            print('CCNC_AUDIT_HOME_ERROR:' + str(error), flush=True)
        if app not in pinned and launcher.alive(app):
            import os
            os.kill(int((launcher.RUN / (app + '.pid')).read_text()), signal.SIGTERM)
            time.sleep(.2)
print('CCNC_APP_AUDIT_DONE', flush=True)
