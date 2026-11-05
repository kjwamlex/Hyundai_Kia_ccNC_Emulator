# ccNC app startup support

The lab starts the original ARM64 Linux/ccOS applications and their original
Qt/Wayland screens. It does not provide Android or model the Tegra hardware.

## What changed

Dashboard launch requests now pass through a small app-scoped compatibility hook
that asks the lab launcher to start the requested executable. After the original
AppService reports lifecycle RUN, the original launch request is forwarded
unchanged. The launcher reads actual appinfo.json files instead of a hand-written
list of dashboard tiles. It honors declared app IDs when they differ from the
executable directory (the supplied Qibla package has this mismatch). It serializes process creation and preserves the normal
base HMIs and original engineering manager. On-demand metadata is changed only in
the guest writable filesystem because vendor systemd activation is absent.

The original SOME/IP routingmanagerd now runs locally. Its guest configuration
uses loopback with network service discovery disabled; no vehicle peers are
fabricated. Lab-state publishes inactive restriction sessions through the real
NodeStateManager, consistent with the existing simulated parked/zero-speed state.
This allows Cinema's own screen to open.

All lab HMIs use Qt's basic render loop to serialize surface changes under Mesa.
A narrow media compatibility guard rejects Pet Care's unsupported video-player
request before it can damage the shared media backend. It also skips listener
registration and rejects setURL on a null player, logging CCNC_MEDIA_UNAVAILABLE.
It preserves failure rather than reporting successful video playback. Original
media methods are resolved through the already-loaded library even when a Qt
plugin loaded that library with local symbol scope.
Verbose DLT output is bounded to approximately 32 MiB, retaining the latest app
lifecycle and input-router readiness records during rotation. Separate atomic
per-app lifecycle records prevent log rotation from causing false launch timeouts.

## Open apps

Restart the dashboard to load these changes. Dashboard tiles use the launcher
automatically. From the VM supervisor console:

```sh
ccnc -c '/opt/ccnc-qemu/open-app.sh cinema'
ccnc -c '/opt/ccnc-qemu/open-app.sh projection'
ccnc -c '/opt/ccnc-qemu/open-app.sh manualhmi'
ccnc -c '/opt/ccnc-qemu/open-app.sh evhmi'
ccnc -c '/opt/ccnc-qemu/open-app.sh radio'
ccnc -c 'python3 /opt/ccnc-qemu/app-launcher.py --list'
```

The helper also accepts an original app directory name and `--service SERVICE`
for apps exporting multiple services. `--scene` requests the first front scene
registered in appinfo.json instead of the first intent, for explicit lab probing.
Support HMIs without a front application window can be started with
`python3 /opt/ccnc-qemu/app-launcher.py --ensure APP`; they are overlays/managers,
not independent dashboard pages. F1–F9 and OEM Back/Home/Menu retain their roles.

## Reproduce the audit

```sh
python3 qemu/run.py --gui ccnc --display none --audio none --job qemu/audit-apps.sh --timeout 1200 --screenshot qemu/artifacts/apps/audit.png
```

Use a disposable VM. The audit starts apps sequentially, returns Home between
tests and terminates optional processes to avoid accumulating regional variants.
It records startup errors, OEM foreground state and screenshots. A foreground
result confirms a screen/lifecycle transition, not functioning vehicle signals,
cloud accounts, phones, tuners, cameras or video hardware. Apps can start and
remain hidden because their original handler refuses an unsupported mode.

Navigation has a small executable wrapper but its linked payload under
`/ccos/navigation/apps/hmi/navihmi` contains zero-length metadata/shader files in
this supplied image. Splashscreen has no normal appinfo.json and is a boot-only
component. The SXM360L radio directory exports the same app ID/executable name as
standard NARADIO and is excluded from automatic activation to avoid conflicts.

## Audit results

Verified on 2026-11-04. All **71 HMI directories** were inspected. **32 components showed a compositor-confirmed window** in the normal or targeted runs; this includes system controls and connection dialogs. This is screen coverage, not a count of fully functional apps.

The normal audit uses registered intents. Targeted checks use registered scenes or a fresh VM to separate startup from regional/backend conflicts. A hidden process is explicitly reported as hidden. The complete run and follow-ups are retained in [support-results.json](artifacts/apps/support-results.json).

The all-region sweep is a stress test: mutually exclusive radio stacks and missing backend sessions can affect later apps. Fresh targeted results are listed alongside the sweep, without replacing its failures. Qibla’s targeted check includes the final app-ID fix.

| App | Normal launch | Targeted follow-up | Limit / entry point |
| --- | --- | --- | --- |
| `alexavrhmi` | Started; hidden | — | Alexa backend/session unavailable. |
| `androidautohmi` | Started; hidden | — | Use Phone Projection for connection setup; no phone session. |
| `audiohmi` | Visible screen | — | Sounds of Nature playback, volume, mute and resume verified. |
| `carlifehmi` | Started; hidden | — | No phone session or projection transport. |
| `carpayhmi` | Started; hidden | — | Vehicle/account/payment backend unavailable. |
| `carplayhmi` | Started; hidden | — | Use Phone Projection for connection setup; no phone session. |
| `cartohomehmi` | Started; hidden | — | Connected-home backend unavailable. |
| `carwashmodehmi` | Started; hidden | — | Vehicle signals unavailable. |
| `ccscontentshmi` | Started; hidden | — | Diagnostics/vehicle backend unavailable. |
| `ccshmi` | Started; hidden | Visible screen | Settings opens with `--scene`; activation/cloud service unavailable. |
| `climatehmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `connectedgaragehmi` | Started; hidden | — | Account, location and camera backend unavailable. |
| `cvccshmi` | Started; hidden | — | OEM handler reports DTG inactive. |
| `dashcamerahmi` | Started; hidden | — | Camera/vehicle backend unavailable. |
| `dmbhmi` | Visible screen | — | UI only; tuner/video unavailable. |
| `ecallhmi` | Started; hidden | — | No modem/emergency-call session. |
| `engineeringmodehmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `euradiohmi` | Started; hidden | Started; hidden | Lifecycle starts, but no visible window confirmed in this Korean configuration. |
| `evhmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `extcamerahmi` | Exited during launch | Exited during launch | Crashes while preparing the original camera scene. |
| `extcameralayerhmi` | Support component ready | — | Vehicle/peripheral actions remain unverified. |
| `fcevhmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `globalsearchhmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `hddatahmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `hevhmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `hipasshmi` | Started; hidden | — | OEM handler rejects launch: power undefined. |
| `homehmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `indiaradiohmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `locationsharinghmi` | Started; hidden | — | Location/connected-service backend unavailable. |
| `manualhmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `mediahomehmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `myvehiclehmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `naradiohmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `naradiohmi-sxm360l` | Missing/conflicting metadata | — | Shares NARADIO identity; binary name conflicts with standard package. |
| `navihmi` | Missing/conflicting metadata | — | Navigation payload metadata/shaders are zero-length in the supplied image. |
| `nmodehmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `offroadmodehmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `passengerviewhmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `petcarehmi` | Started; hidden | Started; hidden | Startup survives unavailable video; main page remains hidden. |
| `phevhmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `phonehmi` | Visible screen | — | UI only; Bluetooth calling unavailable. |
| `phoneprojectionhmi` | Visible screen | — | Original connection dialog opens; projection session unavailable. |
| `qiblahmi` | Startup failed/timeout | Visible screen | Directory qiblahmi declares app ID qibalhmi; launcher now honors metadata. Compass/location unavailable. |
| `quickcontrolhmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `radiohmi` | Startup failed/timeout | Visible screen | Korean radio page opens in fresh targeted run; no tuner reception. |
| `restmodehmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `rfconnsetuphmi` | Support component ready | — | Vehicle/peripheral actions remain unverified. |
| `screensaverhmi` | Support component ready | — | Vehicle/peripheral actions remain unverified. |
| `seathmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `setuphmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `smartthingshmi` | Started; hidden | — | Vehicle/peripheral actions remain unverified. |
| `splashscreenhmi` | Missing/conflicting metadata | — | Boot-only component without normal appinfo.json. |
| `splitscreenhmi` | Support component ready | — | Vehicle/peripheral actions remain unverified. |
| `sportshmi` | Started; hidden | — | Vehicle/peripheral actions remain unverified. |
| `statusbarhmi` | Visible screen | — | System controls; OEM Back/Home/Menu verified. |
| `streaminghmi` | Startup failed/timeout | Started; hidden | Starts in fresh media run; page hidden. Can crash during the all-region stress sweep. |
| `systempopuphmi` | Support component ready | — | Vehicle/peripheral actions remain unverified. |
| `theaterhmi` | Visible screen | Visible screen | Original service selection opens; NVIDIA/WebOS playback unavailable. |
| `trailermodehmi` | Visible screen | — | Vehicle/peripheral actions remain unverified. |
| `updatehmi` | Started; hidden | — | Invoked through Settings → General → USB Update; popup regression passes. |
| `usbvideohmi` | Startup failed/timeout | Started; hidden | Starts in fresh media run; no playback confirmed. Audio-focus path can crash during the broad sweep. |
| `userprofilehmi` | Started; hidden | Started; hidden | Starts; profile/account page remains hidden. |
| `valetmodehmi` | Started; hidden | — | Vehicle/account prerequisites unavailable. |
| `vehicleupdatehmi` | Started; hidden | — | Use Settings USB Update flow; no firmware installation performed. |
| `voicememohmi` | Startup failed/timeout | Visible screen | Original page opens with `--scene`; microphone/recording unverified. |
| `vrcontentplayerhmi` | Support component ready | — | Vehicle/peripheral actions remain unverified. |
| `vrhmi` | Startup failed/timeout | — | No voice recognition session/backend. |
| `vrmediaplayerhmi` | Startup failed/timeout | — | Voice media helper exits during startup in this lab. |
| `weatherhmi` | Started; hidden | Started; hidden | Starts in fresh run; location/cloud data and page unavailable. |
| `webcommonhmi` | Started; hidden | — | Web/vehicle integration remains incomplete. |
| `webosprojectionhmi` | Startup failed/timeout | Started; hidden | Starts in fresh run; WebOS LCP bus/partition unavailable. |

Regression checks: OEM Back/Home/Menu and English↔Korean switching passed. USB Update popup opening, dismissal and reopening passed. Audio capture confirmed stereo playback, silence on mute, resumed playback and the Settings beep, including after the optional media-app audit. The media-isolation capture had RMS levels 171.61 / 0.00 / 176.73 for playback / mute / resume.

Evidence: [complete startup log](logs/complete-live.log), [media isolation log](logs/media-isolation-live.log), [edge cases log](logs/edge-cases-live.log), [app identity check](logs/identity-live.log), [USB update regression](logs/update-regression-live.log). Screenshots use `complete-APP.png`, `media-isolation-APP.png` and `edge-cases-APP.png` under `artifacts/apps/`.
