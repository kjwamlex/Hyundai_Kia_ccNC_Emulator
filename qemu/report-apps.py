#!/usr/bin/env python3
"""Build the app coverage table from actual VM audit records."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent


def records(name):
    path = root / 'logs' / name
    return [json.loads(line.split('CCNC_APP_RESULT:', 1)[1])
            for line in path.read_text().splitlines() if 'CCNC_APP_RESULT:' in line]


def label(row):
    if row is None:
        return '—'
    if row['status'] == 'foreground' and row.get('visible_windows'):
        return 'Visible screen'
    return {'foreground': 'Started; no window confirmed',
            'ready-no-foreground': 'Started; hidden',
            'support-ready': 'Support component ready',
            'no-executable-metadata': 'Missing/conflicting metadata',
            'exited-after-launch': 'Exited during launch',
            'startup-failed': 'Startup failed/timeout'}[row['status']]


baseline = {row['app']: row for row in records('complete-live.log')}
if len(baseline) != 71:
    raise SystemExit('The complete 71-directory audit must finish first')
followups = {row['app']: row for row in records('media-isolation-live.log') + records('edge-cases-live.log') + records('identity-live.log')}
notes = {
    'audiohmi': 'Sounds of Nature playback, volume, mute and resume verified.',
    'statusbarhmi': 'System controls; OEM Back/Home/Menu verified.',
    'alexavrhmi': 'Alexa backend/session unavailable.',
    'androidautohmi': 'Use Phone Projection for connection setup; no phone session.',
    'carlifehmi': 'No phone session or projection transport.',
    'carplayhmi': 'Use Phone Projection for connection setup; no phone session.',
    'carpayhmi': 'Vehicle/account/payment backend unavailable.',
    'cartohomehmi': 'Connected-home backend unavailable.',
    'carwashmodehmi': 'Vehicle signals unavailable.',
    'ccscontentshmi': 'Diagnostics/vehicle backend unavailable.',
    'ccshmi': 'Settings opens with `--scene`; activation/cloud service unavailable.',
    'connectedgaragehmi': 'Account, location and camera backend unavailable.',
    'cvccshmi': 'OEM handler reports DTG inactive.',
    'dashcamerahmi': 'Camera/vehicle backend unavailable.',
    'dmbhmi': 'UI only; tuner/video unavailable.',
    'ecallhmi': 'No modem/emergency-call session.',
    'extcamerahmi': 'Crashes while preparing the original camera scene.',
    'euradiohmi': 'Lifecycle starts, but no visible window confirmed in this Korean configuration.',
    'hipasshmi': 'OEM handler rejects launch: power undefined.',
    'locationsharinghmi': 'Location/connected-service backend unavailable.',
    'naradiohmi-sxm360l': 'Shares NARADIO identity; binary name conflicts with standard package.',
    'navihmi': 'Navigation payload metadata/shaders are zero-length in the supplied image.',
    'petcarehmi': 'Startup survives unavailable video; main page remains hidden.',
    'phonehmi': 'UI only; Bluetooth calling unavailable.',
    'phoneprojectionhmi': 'Original connection dialog opens; projection session unavailable.',
    'qiblahmi': 'Directory qiblahmi declares app ID qibalhmi; launcher now honors metadata. Compass/location unavailable.',
    'radiohmi': 'Korean radio page opens in fresh targeted run; no tuner reception.',
    'splashscreenhmi': 'Boot-only component without normal appinfo.json.',
    'streaminghmi': 'Starts in fresh media run; page hidden. Can crash during the all-region stress sweep.',
    'theaterhmi': 'Original service selection opens; NVIDIA/WebOS playback unavailable.',
    'updatehmi': 'Invoked through Settings → General → USB Update; popup regression passes.',
    'usbvideohmi': 'Starts in fresh media run; no playback confirmed. Audio-focus path can crash during the broad sweep.',
    'userprofilehmi': 'Starts; profile/account page remains hidden.',
    'valetmodehmi': 'Vehicle/account prerequisites unavailable.',
    'vehicleupdatehmi': 'Use Settings USB Update flow; no firmware installation performed.',
    'voicememohmi': 'Original page opens with `--scene`; microphone/recording unverified.',
    'vrhmi': 'No voice recognition session/backend.',
    'vrmediaplayerhmi': 'Voice media helper exits during startup in this lab.',
    'weatherhmi': 'Starts in fresh run; location/cloud data and page unavailable.',
    'webcommonhmi': 'Web/vehicle integration remains incomplete.',
    'webosprojectionhmi': 'Starts in fresh run; WebOS LCP bus/partition unavailable.',
}
visible = [app for app, row in baseline.items()
           if label(row) == 'Visible screen' or label(followups.get(app)) == 'Visible screen']
lines = ['## Audit results', '',
         'Verified on 2026-11-04. All **71 HMI directories** were inspected. '
         f'**{len(visible)} components showed a compositor-confirmed window** in the normal '
         'or targeted runs; this includes system controls and connection dialogs. '
         'This is screen coverage, not a count of fully functional apps.', '',
         'The normal audit uses registered intents. Targeted checks use registered scenes '
         'or a fresh VM to separate startup from regional/backend conflicts. A hidden '
         'process is explicitly reported as hidden. The complete run and follow-ups '
         'are retained in [support-results.json](artifacts/apps/support-results.json).', '',
         'The all-region sweep is a stress test: mutually exclusive radio stacks and '
         'missing backend sessions can affect later apps. Fresh targeted results are '
         'listed alongside the sweep, without replacing its failures. Qibla’s targeted '
         'check includes the final app-ID fix.', '',
         '| App | Normal launch | Targeted follow-up | Limit / entry point |',
         '| --- | --- | --- | --- |']
for app, row in sorted(baseline.items()):
    lines.append(f'| `{app}` | {label(row)} | {label(followups.get(app))} | {notes.get(app, "Vehicle/peripheral actions remain unverified.")} |')
lines += ['', 'Regression checks: OEM Back/Home/Menu and English↔Korean switching passed. '
          'USB Update popup opening, dismissal and reopening passed. Audio capture '
          'confirmed stereo playback, silence on mute, resumed playback and the Settings '
          'beep, including after the optional media-app audit. The media-isolation capture '
          'had RMS levels 171.61 / 0.00 / 176.73 for playback / mute / resume.', '',
          'Evidence: [complete startup log](logs/complete-live.log), '
          '[media isolation log](logs/media-isolation-live.log), '
          '[edge cases log](logs/edge-cases-live.log), '
          '[app identity check](logs/identity-live.log), '
          '[USB update regression](logs/update-regression-live.log). '
          'Screenshots use `complete-APP.png`, `media-isolation-APP.png` and '
          '`edge-cases-APP.png` under `artifacts/apps/`.', '']
report = root / 'APP_SUPPORT.md'
report.write_text(report.read_text().split('## Audit results')[0] + '\n'.join(lines))
(root / 'artifacts/apps/support-results.json').write_text(json.dumps(
    {'normal': baseline, 'followups': followups, 'visible_components': visible}, indent=2))
print(f'Reported {len(baseline)} HMI directories, {len(visible)} visible components')
