# Hyundai ccNC QEMU environment

For prerequisites and a fresh clone, start with the [project setup guide](../README.md).
Firmware and generated evidence are local inputs/outputs and are not included
in the repository. References below to `artifacts/` and `logs/` describe locally
generated files. Optional audit tools may require separately extracted local
vendor files; they are not prerequisites for the dashboard.

This setup boots a generic ARM64 Linux kernel in QEMU and executes the original
ccNC shell and binaries from the supplied ext4 image. The original **homehmi
dashboard** now renders at 1920×720 with the original Weston IVI shell and ccOS
window manager. Mesa llvmpipe executes the Qt OpenGL effects on the CPU.

This is a partial userspace port, not a Tegra186 hardware model. App cards,
wallpaper, Korean text, guest selection, pointer delivery, and the original Media
source menu work. Phone, RF connection setup, Audio, and Settings HMIs are preloaded too.
The original audio policy service uses a QEMU output HAL in place of the physical
DSP HAL. Sounds of Nature plays through ALSA and QEMU HDA. The Home media card renders its
original Media / Off state, artwork, play control and source button. Other OEM media sources, Bluetooth calling, navigation, phone
projection, cameras, vehicle data, and NVIDIA cross-partition/hypervisor features
remain incomplete. The complete vendor boot graph is not started.

The app launcher now reads the firmware catalog and starts additional HMIs on
their original dashboard launch requests. The 71-directory audit confirmed visible
windows from 32 apps/system components, including connection dialogs. Some apps
start but remain hidden or require missing backends. See [app startup support and
audit](APP_SUPPORT.md) for per-app results, limitations and direct launch commands.

## Start the dashboard

Double-click **Launch dashboard.command**, or from the firmware folder:

```sh
python3 qemu/run.py --gui ccnc --state
```

Allow about 25–40 seconds on Apple Silicon. The serial console prints
`CCNC_HMI_READY` after the original home window reaches foreground, followed by
`CCNC_APPS_READY` when the app processes and navigation keys are ready. Click the
QEMU window to interact. Media and Phone cards can launch their original HMIs.
Apps also have the original bottom-left **Back, Home and Menu** controls.
The OEM `statusbarhmi` supplies the bar, `uinput` supplies its virtual key device,
and `window-input-router` delivers Back/Menu to the focused app through the
original compositor protocol. Home launches the original dashboard. Visibility
and disabled states follow the OEM window policy; the bar is hidden on Home.
Keyboard shortcuts in the QEMU window: **F1 Home, F2 Media, F3 Phone, F4 Audio,
F5 Settings, F6 welcome animation, F7 goodbye animation, F8 one-second audio test tone,
F9 engineering password screen**
(use Fn on keyboards with media function keys).
The macOS dashboard launcher enables CoreAudio output by default; use
`--audio off` to omit sound hardware or `--audio none` for silent HDA testing.
The dashboard and serial-shell launchers save filesystem changes in
`qemu/state/ccnc.qcow2`. The original firmware image is attached read-only
throughout. Shut down with `poweroff -f` from the supervisor shell to flush writes.

Change language in **Settings → General → Language → English / 한국어**.
The original `setupmanager` applies the choice through HSystem and updates the
app translations. A lab helper saves guest user `0`'s valid HSystem language in
`/ccos/data/ccnc-qemu/guest-0-language.json` and restores it before the HMIs start.
With `--state`, the choice survives reboot; a disposable RAM session loses it.
Korean is the fallback on a first boot with no valid system language.

For a simple compositor diagnostic use `--gui desktop` or **Launch graphics.command**.
This starts the original Weston desktop shell with its shared-memory sample;
it is a separate diagnostic, not the dashboard.

### Engineering-mode entry

Restart the dashboard after installing these files, then press **F9** (or **Fn+F9**)
in its QEMU window. This opens the original engineering password keyboard. A valid
engineering password is still required; no password has been verified for this
build. **F1** returns to Home.

From the supervisor console attached to the dashboard VM, the equivalent is:

```sh
ccnc -c '/opt/ccnc-qemu/open-app.sh engineering'
```

The helper starts the original `engineeringmodemanager` and `engineeringmodehmi`,
then sends the `ENGINEERINGMODE` / `ENGMODE_MAIN` intent through AppService.
It marks the HMI as preloaded in the guest's writable filesystem because the
vendor systemd activation path is absent in this lab. The original image stays
read-only. A preload scoped to the engineering HMI preserves nonempty DSP version
replies and replaces empty ones with `Unavailable`: the OEM display otherwise
writes before its empty string and crashes. This does not emulate a DSP.

The original password screen was rendered and captured with:

```sh
python3 qemu/run.py --gui ccnc --display none --audio none --job qemu/probe-engineering.sh --screenshot qemu/artifacts/display/engineering.png --timeout 150
```

This verifies entry to the password screen, not access to the authenticated menus
or a hidden tap sequence on a physical head unit.

The original Settings tap sequence has also been verified in a disposable VM:
hold FM audio focus at volume **2**, open **General → SW Info/Update**, then tap
**(1462,544) five times** and **(1862,544) once** on the Korean 1920×720 layout.
Settings itself launches the engineering password screen. These coordinates
have not been verified on physical hardware or other layouts. The investigation
report contains the recovered QML, audio gate details, screenshots, and logs.

The password investigation is documented in
[`artifacts/engineering-password-audit/INVESTIGATION.md`](artifacts/engineering-password-audit/INVESTIGATION.md).
All numeric engineering passwords through nine digits have been excluded for
this build. `2400` is the dealer code. The embedded vehicle-support code
`30153015` is rejected because its success path is disabled in the original
binary. The yearly engineering password remains unknown. Use
`python3 qemu/engineering-password-check.py CANDIDATE --year 2026`
for an offline check against this build; omit `--year` to model its invalid-clock
fallback. Offline checks do not consume password attempts.

### Welcome and goodbye shortcuts

Press **F6** in the dashboard window to replay the original Hyundai welcome video;
**F7** replays the goodbye video without shutting down. Playback returns to Home.
Repeated presses during playback are ignored. These shortcuts use CPU video decoding
and temporarily pause Weston while displaying frames, since the factory animation
service requires an NVIDIA video sink.

The default clips are `/ccos/services/welcomeaniservice/lhd/welcome_hyundai_avnt.264`
and `goodbye_hyundai_avnt.264`. To override them, place raw H.264 clips at
`/ccos/data/qemu/welcome.264` and `/ccos/data/qemu/goodbye.264` inside the guest.
Clips are fitted to the display with their aspect ratio preserved and limited to
15 seconds. Changes persist when using `--state`.

These raw video files contain no sound. Optional `/ccos/data/qemu/welcome.wav`
and `/ccos/data/qemu/goodbye.wav` play alongside the corresponding video through
the configured audio output. Without those files, playback is silent. Logs are
in `/tmp/ccnc-qemu/animation.log` inside the guest.

The keyboard integration check plays both clips, checks that Weston resumes, and
captures the Home screen, both animations, and audio:

```sh
python3 qemu/run.py --gui ccnc --display none --audio wav --audio-file qemu/artifacts/display/welcome-test.wav --job qemu/test-welcome.sh --screenshot qemu/artifacts/display/welcome-test.png --welcome-test
```

## Start a serial shell

Double-click **Launch ccNC.command** in this directory, or run from the firmware
folder:

```sh
python3 qemu/run.py --state
```

At the VM prompt, enter the firmware environment:

```sh
ccnc
cat /etc/os-release
ls /ccos/apps
ls /ccos/services
```

`exit` returns to the small Alpine supervisor shell. Run `poweroff -f` there to
stop, or press **Ctrl-a**, release, then **x** to quit QEMU.

Apple Silicon uses HVF hardware acceleration automatically. Software emulation:

```sh
python3 qemu/run.py --accel tcg
```

Defaults: two virtual CPUs, 4 GiB RAM for ccNC GUI (2 GiB otherwise), serial console, no network adapter.
Options include `--memory 4096`, `--cpus 4`, and `--dry-run`.

## Filesystem behavior

- `system/1_gos1-fs_7_ext4.img` is attached as a **read-only** raw block device.
  It is already a filesystem image, so no partition-table reconstruction is needed.
- `/firmware` is mounted with `ro,noload`, preventing journal replay.
- `/ccnc` is the writable firmware filesystem. Enter it with `ccnc`; paths such
  as `/etc` and `/ccos` are then writable.
- `--state` saves writes in `qemu/state/ccnc.qcow2`, creating that disk on first
  use. `--state /absolute/path/lab.qcow2` selects a separate persistent disk.
  Only changed blocks occupy host disk space; the original 11 GiB image is not copied.
- Without `--state`, `/ccnc` uses a disposable overlay with up to 768 MiB of RAM
  for writes. These changes disappear when the VM stops.
- `/proc`, `/sys`, `/dev`, `/run`, and `/tmp` are provided inside `/ccnc`.
- `ccnc -c 'command'` runs a command with the firmware shell and original libraries.
- `/run` and `/tmp` remain temporary in either mode. `--overlay` files (including
  GUI compatibility files) are copied into `/ccnc` again on each boot.
- Use one VM per state disk. To reset persistent changes, stop the VM and rename
  its qcow2 file; the next launch creates a fresh state disk. Keep the original
  firmware image in place because the state disk depends on it.

For example, create a file with `ccnc -c 'echo hello > /root-example.txt'` in the
supervisor shell. With `--state`, it is still present after shutting down and
starting again with the same state disk. `/firmware` stays read-only; use `/ccnc`
or the `ccnc` shell to make changes.

The Alpine init script is PID 1. This setup does not start the vendor's systemd
service graph; `systemctl` inside the chroot cannot manage a ccNC systemd instance.
Programs requiring vendor devices, external services, or their kernel ABI can
still fail even though ordinary ARM64 binaries execute.

## Verified

Both commands passed on this Apple Silicon Mac with QEMU 11.1.3:

```sh
python3 qemu/run.py --smoke --accel hvf
python3 qemu/run.py --smoke --accel tcg
```

The checks execute the original `/bin/sh`, `uname`, `cat`, and `ls`, verify the
`/ccos/apps` and `/ccos/services` directories, write a file through the RAM overlay,
confirm it is absent from the lower filesystem, and check that the guest block
device is read-only. The VM then powers off. Logs are in `logs/smoke-hvf.log` and
`logs/smoke-tcg.log`; `logs/smoke.log` holds the most recent run.

Persistent mode also passed `--smoke --state --accel hvf`. A two-boot check wrote
files under `/etc` and `/ccos`, read them after restarting with the same state
disk, and confirmed the original firmware SHA-256 was unchanged. `qemu-img check`
reported no errors on the test state disk.

Firmware identity:

```text
NAME="Pony (ccOS Reference Distro)"
VERSION="5.0.49.0-40756073 (pony)"
BUILD_ID="20260813164608"
MACHINE_ID="mst6g"
```

## Why the supplied kernel cannot boot this QEMU machine

The recovered DTB identifies `nvidia,p2382_t186`, `nvidia,tegra186`. The supplied
Linux kernel is **4.9.299-tegra**, built for NVIDIA's automotive hypervisor.
Installed QEMU has no Tegra186/P2382 machine model.

The embedded kernel configuration also explicitly disables the drivers required
by QEMU's `virt` board:

```text
# CONFIG_SERIAL_AMBA_PL011 is not set
# CONFIG_VIRTIO_BLK is not set
# CONFIG_VIRTIO_PCI is not set
# CONFIG_VIRTIO_MMIO is not set
# CONFIG_PCI_HOST_GENERIC is not set
CONFIG_TEGRA_HV_BLKDEV=y
CONFIG_TEGRA_HV_MANAGER=y
```

The update manifest expects `/dev/vblkdev2p1`, an NVIDIA hypervisor disk. This
environment instead exposes that filesystem as virtio `/dev/vda` to the generic
kernel, then mounts it at `/ccnc`.

Pointing QEMU at the vendor DTB would describe hardware that QEMU does not
implement. Full fidelity would require a Tegra186 machine model, NVIDIA
hypervisor interfaces, and peripheral models. The implemented userspace port
uses virtio GPU's framebuffer, Weston's fbdev/pixman backend, and an isolated
Mesa EGL/GLES stack for homehmi. It omits NVIDIA cross-partition output and
shared-texture extensions; it does not emulate NVIDIA hardware.

## Dashboard compatibility and verification

`graphics-init.sh` supplies CPU cgroup v1 groups, shared memory, USB input and
udev classification. `overrides/opt/ccnc-qemu/start-gui.sh` starts the original
D-Bus, NodeStateManager, shared data, memory, persistence, application, user,
variant, clock and system services, then Weston, appeventmanager and homehmi.
It starts audioservice, mediaservice and mediagatemanager before Home so the
initial media state is available when Home creates its card. After selecting the
user, it preloads rfconnsetuphmi, phonehmi, audiohmi, mediahomehmi and setuphmi with
exact application readiness checks. Each HMI includes its own local QML plugin directory in the import path.
`show-home.sh` waits for lifecycle readiness, selects existing guest user `0`,
registers a synthetic boot-complete session and launches `HOME.Main`
through the original AppService. These are lab lifecycle inputs.
`language-state.py` restores the saved language or initializes Korean only when
HSystem reports an invalid language. `start-settings.sh` starts the original
setupmanager with its vendor environment and waits for its Settings D-Bus API
before preloading the HMIs. The startup no longer forces Korean on every boot.

`compat/ashmem-memfd.c` replaces the original library's five ashmem entry points
with memfd equivalents. Mesa 20.3.5 / LLVM 11 runs the original Qt 6 shader effects
on the CPU. Plain `QT_QUICK_BACKEND=software` loses the shader-based masked
artwork. Mesa libraries are scoped to each HMI via `LD_LIBRARY_PATH`; original
firmware binaries and lower filesystem are unchanged.

Run from the firmware folder:

```sh
python3 qemu/run.py --job qemu/test-ashmem.sh --overlay qemu/overrides
python3 qemu/run.py --gui desktop --display none --job qemu/test-graphics.sh --screenshot qemu/artifacts/display/desktop.png
python3 qemu/run.py --gui ccnc --display none --job qemu/test-hmi.sh --screenshot qemu/artifacts/display/home.png --pointer-test
```

The HMI test checks original processes, foreground lifecycle, the loaded Mesa
software driver, and compositor pointer classification. It captures the actual
QEMU display through QMP, clicks the Phone card through the emulated USB tablet,
and requires homehmi's QML click handler to log the event. It does not claim the
Phone application's backend works. `--pointer-test` is required for that job.
Logs are under `qemu/logs/`; inside the firmware shell use
`/tmp/ccnc-qemu/{weston,homehmi,dlt,show-home}.log`.

The media card depends on media policy and NowPlaying state during Home startup.
Starting them before Home fixes the blank card and displays the original Off state.
Preloading the HMIs fixes missing app registrations; it does not create a radio,
Bluetooth or USB source. `probe-media.sh` inspects the running stack and opens
Audio. It must be used with `--gui ccnc` and does not start duplicate services.

## Audio and app checks

The audio path uses a separate, pinned Alpine LTS kernel because the small virt
kernel omits sound drivers. QEMU presents Intel HDA with an output-only codec.
The RAM overlay supplies ALSA aliases (`default`, `AV1_OUT`, `HD_OUT`, `NAVI_OUT`,
`NAVI_WARNING_OUT`) backed by a shared HDA PCM device; startup unmutes Master.

The original audioservice retains its policy/focus/settings IPC and original route
configuration. `compat/audiohal-qemu.cpp` implements this firmware's IHALAudio
binary interface. It replaces `libaudiohal.mobis.mst6g.so` only in the RAM overlay.
Asynchronous route callbacks use the OEM completion enum, and stream queries
return its status-plus-list structure with stereo S16_LE / 48 kHz ALSA metadata.
The original media decoder writes PCM; the adapter does not substitute a test
recording for OEM content. Separate ALSA softvol controls handle media, navigation,
and beep gain/mute before mixing into the HDA device. Beeps use short synthesized
lab tones, not the vehicle's DSP waveform. Settings for EQ, balance/fader and
vehicle-specific sound processing report unsupported; those DSP effects are not
implemented. The output remains a single stereo device, without physical speaker
zones or microphone capture.

The scoped `libaudio-platform-qemu.so` returns ENODEV immediately from the absent
camera-controller request, avoiding its startup watchdog. Mediaservice
uses a private plugin discovery directory excluding NVIDIA and GPU rendering
plugins while retaining the CPU audio/video converters. Audio is opened through
the original `MEDIA_AUDIO` intent; direct `MEDIA.Audio` scene requests are rejected
by its app service.

```sh
python3 qemu/run.py --gui ccnc --display none --audio none --job qemu/test-apps.sh --screenshot qemu/artifacts/display/media.png --apps-test
python3 qemu/run.py --audio wav --audio-file qemu/artifacts/display/audio-test.wav --overlay qemu/overrides --job qemu/test-audio.sh
python3 qemu/verify-audio.py qemu/artifacts/display/audio-test.wav
```

The app test injects keyboard events and checks Media, Phone, Audio and Home
foreground transitions. The low-level audio test and verifier check the generic
440 Hz tone. The routing test exercises Settings, Sound and General with actual
pointer events, opens Sounds of Nature, and controls OEM media volume/mute through
the original HAudioController API. It records screenshots and a WAV with phase
byte offsets for signal verification:

```sh
python3 qemu/run.py --gui ccnc --display none --audio wav --audio-file qemu/artifacts/display/routing-test.wav --job qemu/test-routing.sh --screenshot qemu/artifacts/display/routing-test.png --routing-test --timeout 150
python3 qemu/verify-routing.py qemu/artifacts/display/routing-test.wav
```

The navigation regression clicks the OEM bar: General → Back → Settings, Menu
open/dismiss/reopen, then Home from Settings and Media. It checks the latest
Settings scene and compositor window visibility, including the options panel:

```sh
python3 qemu/run.py --gui ccnc --display none --audio none --job qemu/test-navigation.sh --screenshot qemu/artifacts/navigation/verified.png --navigation-test --timeout 150
```

The language regression requires a **new** state disk for its first run. It
clicks English → Korean → English in Settings, checks HSystem and the saved
value, then checks English again in a separate boot using the same disk:

```sh
python3 qemu/run.py --gui ccnc --display none --audio none --state qemu/artifacts/language/language-regression.qcow2 --job qemu/test-language.sh --screenshot qemu/artifacts/language/switched.png --language-test --timeout 150
python3 qemu/run.py --gui ccnc --display none --audio none --state qemu/artifacts/language/language-regression.qcow2 --job qemu/test-language-restore.sh --screenshot qemu/artifacts/language/restored.png --timeout 150
```

Inside the firmware shell, lab audio controls are available through
`/opt/ccnc-qemu/audio-control.py volume 0..45`, `mute`, `unmute`, and `beep`.
These call the firmware's public audio API, including the normal policy service.
The helper's opaque parameter layout and enum values are specific to libhaudio
2.6.17 in this supplied image.

Settings uses the original `updateservice` D-Bus API when the update stack is
ready. Its former unavailable-query preload remains a fallback for standalone
Settings launches. The emulator now starts the OEM IAC service, popup manager,
updatehmi and vehicleupdatehmi. F5 opens the original SETUP_GATE intent.

Audio and update HMIs use Qt's basic render loop to serialize rendering with
surface changes. Bluetooth, radio and vehicle DSP processing remain incomplete.

## USB update research

`lab-state.py` supplies explicit simulated ignition-on, parked and zero-speed
inputs through the OEM power/hardwire APIs, plus camera-off state through the
front-center camera API. It starts before appeventmanager: an absent camera
service otherwise leaves camera mode at `max`, causing the original popup manager
to hide update dialogs. It also adapts the lab USB mount to
the OEM DeviceManager API. These are emulator inputs, not observed vehicle state.
The actual Settings button, IAC request, update UI, scanner and update service
come from the supplied firmware. No package-acceptance or signature-success
response is synthesized.

Create a disposable USB fixture and attach it as read-only media:

```sh
python3 qemu/make-usb.py qemu/fixtures/usb-empty qemu/artifacts/update/usb-empty.img --size-mib 64
python3 qemu/run.py --gui ccnc --usb-image qemu/artifacts/update/usb-empty.img
```

`make-usb.py` copies a directory into a new raw ext4 image and refuses to overwrite
an existing file. A raw ext4 volume has been tested. The mount code also supports
FAT/exFAT and the first partition of a disk image; those paths are unverified.
`--usb-image` uses QEMU USB mass storage with
both block layers read-only. The guest mounts it at `/run/media/USB_Front` with
`ro,nosuid,nodev,noexec` (and `noload` for ext4). The original firmware disk also
stays read-only; service writes go to `/ccnc` (RAM by default, persistent with `--state`). Reboot to
change fixtures. Hotplug and automatic unmount are not implemented.

In Settings, open **일반 → SW 정보/업데이트 → USB로 업데이트**. The first
installed-version scan takes about a minute; clicking during it displays the
original “version check in progress” dialog. Once it finishes, absent media and
the empty fixture display the original request to connect a USB containing update
software. **확인** dismisses the dialog, and the button can be used again.

The empty fixture contains no update package. A decrypted filesystem folder is
not automatically a valid signed USB update distribution. Package compatibility,
secure-service dependencies and actual flashing are separate from USB discovery.
QEMU still lacks NVIDIA hypervisor, secure hardware, MICOM and vehicle ECU update
interfaces. This setup does not establish that flashing or cryptographic
validation can complete.

```sh
python3 qemu/run.py --gui ccnc --display none --audio none --job qemu/test-update.sh --screenshot qemu/artifacts/update/no-usb.png --update-test --timeout 150
python3 qemu/run.py --gui ccnc --display none --audio none --usb-image qemu/artifacts/update/usb-empty.img --job qemu/test-update.sh --screenshot qemu/artifacts/update/usb-empty.png --update-test --timeout 150
```

The regression injects real pointer events, requires delivery of APP_REQUEST_UPDATE
to UPDATE, waits for the OEM version-scan completion, and checks the absent-USB
branch or read-only mounted fixture and scanner activity. It queries the OEM
compositor to require a visible, focused update popup, clicks Confirm, verifies
dismissal, then opens it again. Inspect
`qemu/logs/test-update.log` for original updater decisions. Inside the firmware
shell, `/tmp/ccnc-qemu/lab-state.log` records adapter calls and
`/tmp/ccnc-qemu/dlt.log` contains the OEM logs. `probe-update.sh` introspects the
running updater without starting a duplicate instance.

For manual headless capture, add `--qmp /tmp/ccnc-qmp.sock`, then run
`python3 qemu/qmp.py /tmp/ccnc-qmp.sock /tmp/ccnc.png`.


## Rebuild the artifacts

Installed host tools: QEMU, e2fsprogs, and dtc through Homebrew; LZ4 was already
available. Rebuilding requires Python 3 and LZ4; dtc additionally emits readable
device trees. e2fsprogs is useful for offline inspection.

```sh
env HOMEBREW_NO_AUTO_UPDATE=1 brew install qemu e2fsprogs dtc lz4
python3 qemu/prepare.py
env HOMEBREW_NO_AUTO_UPDATE=1 brew install llvm lld
python3 qemu/compat/build.py
python3 qemu/compat/prepare-mesa.py
python3 qemu/prepare-audio.py
```

`prepare.py` strips the outer `BOOT_IMAGE!` and `GSHV` headers from the Linux
kernels and recovery ramdisk, decompresses the exact LZ4 frame without alignment
padding, extracts the DTBs and embedded kernel config, and builds a custom
initramfs. Recovered originals are in `artifacts/vendor/` for inspection; they
are not substituted into the generic boot path.

The boot kernel and initial initramfs come from Alpine Linux 3.22 ARM64 netboot,
kernel **6.12.114-0-virt**. Matching ext4 modules are added from
`linux-virt-6.12.114-r0.apk`. Download URLs and pinned SHA-256 hashes are recorded
in `sources.json`. Downloads stay in `artifacts/alpine/` and are verified on
rebuild. The upstream netboot URLs are rolling: if their contents change, the
script refuses a hash mismatch. Keep the cached files to reproduce this setup.

The compatibility build needs Homebrew LLVM and lld. The audio HAL also uses
SHA-256-pinned ARM64 GNU C++ headers listed in `compat/sysroot-sources.json`;
`compat/prepare-sysroot.py` extracts them under `artifacts/sysroot` without running
package scripts or changing the host toolchain. `prepare-mesa.py` downloads
SHA-256-pinned Debian bullseye ARM64 packages listed in `compat/mesa-sources.json`,
caches the original packages under `artifacts/mesa/`, and places only their
library subtree under `overrides/opt/ccnc-qemu/mesa/`. Only the swrast DRI driver
is installed. No Debian package scripts run and no packages are installed on the
host or into the original firmware. The original `.deb` packages include license
and copyright information. The generated Mesa payload is about 116 MiB and uses
part of the guest's disposable overlay.

The audio path uses Alpine **6.12.115-0-lts**, pinned in `audio-sources.json`.
`prepare-audio.py` verifies the cached APK, extracts its kernel and a minimal
46-module dependency closure (audio, USB storage, filesystems and uinput), and builds `ccnc-audio-initramfs.cpio.gz`. Re-run
it after editing `guest-init.sh`. The host epoch initializes the LTS guest clock.
