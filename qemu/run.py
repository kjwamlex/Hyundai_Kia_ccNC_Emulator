#!/usr/bin/env python3
"""Boot ccNC userspace on QEMU's ARM virt machine, never writing to firmware."""
import argparse
import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def finalize_wav(path):
    """QEMU's WAV backend can leave lengths zero on guest-requested shutdown."""
    import struct
    if path is None or not path.exists():
        return
    with path.open("r+b") as stream:
        header = stream.read(44)
        size = path.stat().st_size
        if len(header) != 44 or header[:4] != b"RIFF" or header[8:16] != b"WAVEfmt " or header[36:40] != b"data":
            raise RuntimeError("Unexpected QEMU WAV container")
        if size - 8 > 0xffffffff:
            raise RuntimeError("QEMU WAV capture exceeds RIFF's 4 GiB limit")
        stream.seek(4)
        stream.write(struct.pack("<I", size - 8))
        stream.seek(40)
        stream.write(struct.pack("<I", size - 44))


def run_with_capture(cmd, timeout, output, qmp_socket, pointer_test=False, apps_test=False, routing_test=False, audio_file=None, update_test=False, welcome_test=False, navigation_test=False, language_test=False):
    import selectors
    import time
    from qmp import screenshot, click, send_key
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    transcript = bytearray()
    deadline = time.monotonic() + timeout
    captured = False
    clicked = False
    keys_sent = set()
    phases = {}
    route_actions = [
        (b"CCNC_SETTINGS_KEY_READY", lambda: send_key(qmp_socket, "f5")),
        (b"CCNC_SETTINGS_SOUND_CLICK", lambda: click(qmp_socket, 470, 210)),
        (b"CCNC_SETTINGS_GATE_AGAIN", lambda: send_key(qmp_socket, "f5")),
        (b"CCNC_SETTINGS_GENERAL_CLICK", lambda: click(qmp_socket, 1400, 480)),
        (b"CCNC_ROUTE_AUDIO_READY", lambda: send_key(qmp_socket, "f4")),
        (b"CCNC_ROUTE_NATURE_CLICK", lambda: click(qmp_socket, 270, 280)),
    ]
    live_log = (HERE / "logs" / (output.stem + "-live.log")).open("wb")
    try:
        while selector.get_map():
            if time.monotonic() >= deadline:
                process.kill()
                tail, _ = process.communicate()
                raise subprocess.TimeoutExpired(cmd, timeout, output=bytes(transcript) + tail)
            for key, _ in selector.select(0.5):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                transcript.extend(chunk)
                live_log.write(chunk)
                live_log.flush()
                if not captured and b"CCNC_CAPTURE_READY" in transcript:
                    screenshot(qmp_socket, output)
                    captured = True
                # Audit markers are emitted only by an explicitly supplied guest job.
                import re
                for match in re.finditer(rb"CCNC_APP_SHOT:([a-z0-9_-]+)\r?\n", transcript):
                    label = match.group(1)
                    marker = b"app-shot-" + label
                    if marker not in keys_sent:
                        screenshot(qmp_socket, output.with_name(output.stem + "-" + label.decode() + output.suffix))
                        keys_sent.add(marker)
                if pointer_test and not clicked and b"CCNC_INPUT_READY" in transcript:
                    click(qmp_socket, 810, 300)
                    clicked = True
                if apps_test:
                    for marker, key in [(b"CCNC_MEDIA_KEY_READY", "f2"), (b"CCNC_PHONE_KEY_READY", "f3"), (b"CCNC_AUDIO_KEY_READY", "f4"), (b"CCNC_HOME_KEY_READY", "f1")]:
                        if marker in transcript and marker not in keys_sent:
                            send_key(qmp_socket, key)
                            keys_sent.add(marker)
                if update_test:
                    for marker, action in [
                        (b"CCNC_UPDATE_SETTINGS", lambda: send_key(qmp_socket, "f5")),
                        (b"CCNC_UPDATE_GENERAL", lambda: click(qmp_socket, 1400, 480)),
                        (b"CCNC_UPDATE_CLICK", lambda: click(qmp_socket, 1150, 650)),
                        (b"CCNC_UPDATE_DISMISS", lambda: click(qmp_socket, 960, 465)),
                        (b"CCNC_UPDATE_REOPEN", lambda: click(qmp_socket, 1150, 650)),
                    ]:
                        if marker in transcript and marker not in keys_sent:
                            action()
                            keys_sent.add(marker)
                if welcome_test:
                    for label, key in [('welcome', 'f6'), ('goodbye', 'f7')]:
                        marker = ('CCNC_' + label.upper() + '_KEY_READY').encode()
                        if marker in transcript and marker not in keys_sent:
                            send_key(qmp_socket, key)
                            keys_sent.add(marker)
                        marker = ('CCNC_SHOT_' + label).encode()
                        if marker in transcript and marker not in keys_sent:
                            screenshot(qmp_socket, output.with_name(output.stem + '-' + label + output.suffix))
                            send_key(qmp_socket, key)  # Repeated presses must not overlap playback.
                            keys_sent.add(marker)
                    marker = b'CCNC_SHOT_restored'
                    if marker in transcript and marker not in keys_sent:
                        screenshot(qmp_socket, output.with_name(output.stem + '-restored' + output.suffix))
                        keys_sent.add(marker)
                if navigation_test:
                    for marker, action in [
                        (b"CCNC_NAV_SETTINGS", lambda: send_key(qmp_socket, "f5")),
                        (b"CCNC_NAV_GENERAL", lambda: click(qmp_socket, 1400, 480)),
                        (b"CCNC_NAV_BACK", lambda: click(qmp_socket, 80, 675)),
                        (b"CCNC_NAV_MENU", lambda: click(qmp_socket, 387, 675)),
                        (b"CCNC_NAV_DISMISS", lambda: click(qmp_socket, 80, 675)),
                        (b"CCNC_NAV_REOPEN", lambda: click(qmp_socket, 387, 675)),
                        (b"CCNC_NAV_HOME", lambda: click(qmp_socket, 235, 675)),
                        (b"CCNC_NAV_MEDIA", lambda: send_key(qmp_socket, "f2")),
                        (b"CCNC_NAV_MEDIA_HOME", lambda: click(qmp_socket, 235, 675)),
                    ]:
                        if marker in transcript and marker not in keys_sent:
                            action()
                            keys_sent.add(marker)
                    marker = b'CCNC_NAV_MENU_SHOT'
                    if marker in transcript and marker not in keys_sent:
                        screenshot(qmp_socket, output.with_name(output.stem + '-menu' + output.suffix))
                        keys_sent.add(marker)
                if language_test:
                    for marker, action in [
                        (b"CCNC_LANG_SETTINGS", lambda: send_key(qmp_socket, "f5")),
                        (b"CCNC_LANG_GENERAL", lambda: click(qmp_socket, 1400, 480)),
                        (b"CCNC_LANG_PAGE", lambda: click(qmp_socket, 220, 465)),
                        (b"CCNC_LANG_ENGLISH", lambda: click(qmp_socket, 800, 360)),
                        (b"CCNC_LANG_KOREAN", lambda: click(qmp_socket, 800, 240)),
                        (b"CCNC_LANG_ENGLISH_AGAIN", lambda: click(qmp_socket, 800, 360)),
                        (b"CCNC_LANG_HOME", lambda: click(qmp_socket, 235, 675)),
                    ]:
                        if marker in transcript and marker not in keys_sent:
                            action()
                            keys_sent.add(marker)
                    marker = b'CCNC_LANG_SHOT'
                    if marker in transcript and marker not in keys_sent:
                        screenshot(qmp_socket, output.with_name(output.stem + '-settings' + output.suffix))
                        keys_sent.add(marker)
                if routing_test:
                    for marker, action in route_actions:
                        if marker in transcript and marker not in keys_sent:
                            action()
                            keys_sent.add(marker)
                    for label in ("gate", "sound", "general", "nature"):
                        marker = ("CCNC_SHOT_" + label).encode()
                        if marker in transcript and marker not in keys_sent:
                            screenshot(qmp_socket, output.with_name(output.stem + "-" + label + output.suffix))
                            keys_sent.add(marker)
                    if audio_file:
                        for label in ("high_start", "high_end", "mute_start", "mute_end", "resume_start", "resume_end"):
                            marker = ("CCNC_PCM_" + label).encode()
                            if marker in transcript and label not in phases:
                                phases[label] = audio_file.stat().st_size
        if phases:
            audio_file.with_suffix(".phases.json").write_text(json.dumps(phases, indent=2))
        status = process.wait(timeout=5)
        if not captured:
            transcript.extend(b"\nCCNC_HOST_ERROR: capture-ready marker was never received\n")
            status = 1
        return subprocess.CompletedProcess(cmd, status, bytes(transcript))
    finally:
        selector.close()
        live_log.close()
        process.stdout.close()
        if process.poll() is None:
            process.kill()
            process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accel", choices=["auto", "hvf", "tcg"], default="auto")
    parser.add_argument("--memory", type=int, help="Guest RAM in MiB (4096 for ccNC GUI, otherwise 2048)")
    parser.add_argument("--cpus", type=int, default=2)
    parser.add_argument("--smoke", action="store_true", help="Boot, check firmware commands, power off")
    parser.add_argument("--job", type=Path, help="Run a supervisor shell script in the VM, then power off")
    parser.add_argument("--timeout", type=int, default=120, help="Smoke/job timeout in seconds")
    parser.add_argument("--display", choices=["none", "cocoa"], help="Native window, or headless (default: cocoa for --gui, otherwise none)")
    parser.add_argument("--gui", choices=["desktop", "ccnc"], help="Start firmware Weston; ccnc starts the original home HMI using CPU OpenGL")
    parser.add_argument("--brand", choices=["hyundai", "kia"],
                        help="Select ccNC branding, theme and animations (saved with --state; otherwise keep the saved/firmware brand)")
    parser.add_argument("--gpu", action="store_true", help="Add virtio GPU even with no display window")
    parser.add_argument("--audio", choices=["off", "coreaudio", "wav", "none"], help="Output-only HDA sound backend (default: CoreAudio for ccNC GUI on macOS, otherwise off)")
    parser.add_argument("--audio-file", type=Path, help="Output WAV file for --audio wav")
    parser.add_argument("--qmp", type=Path, help="Expose a local QMP Unix socket for screenshots/debugging")
    parser.add_argument("--usb-image", type=Path, help="Read-only raw USB filesystem/disk image for the OEM update scanner")
    parser.add_argument("--overlay", type=Path, help="Copy local files into the guest RAM overlay at boot")
    parser.add_argument("--state", type=Path, nargs="?", const=HERE / "state/ccnc.qcow2",
                        help="Persist firmware writes in a qcow2 disk (default path: qemu/state/ccnc.qcow2)")
    parser.add_argument("--screenshot", type=Path, help="For --job: capture PNG when the guest prints CCNC_CAPTURE_READY")
    parser.add_argument("--pointer-test", action="store_true", help="For a screenshot job: click the Phone card on CCNC_INPUT_READY")
    parser.add_argument("--apps-test", action="store_true", help="For a screenshot job: inject Media/Phone/Home shortcut keys on guest markers")
    parser.add_argument("--routing-test", action="store_true", help="For test-routing.sh: exercise Settings and OEM playback via QMP")
    parser.add_argument("--update-test", action="store_true", help="For test-update.sh: click Settings > General > USB update")
    parser.add_argument("--welcome-test", action="store_true", help="For test-welcome.sh: trigger F6/F7 and capture animations")
    parser.add_argument("--navigation-test", action="store_true", help="For test-navigation.sh: click original Back, Home and Menu buttons")
    parser.add_argument("--language-test", action="store_true", help="For test-language.sh: select English/Korean through Settings")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.brand and args.gui != "ccnc":
        parser.error("--brand requires --gui ccnc")
    if args.usb_image:
        args.usb_image = args.usb_image.resolve()
        if not args.usb_image.is_file():
            parser.error("--usb-image must be an existing raw image file")
    if args.memory is None:
        args.memory = 4096 if args.gui == "ccnc" else 2048
    if args.audio is None:
        args.audio = "coreaudio" if args.gui == "ccnc" and platform.system() == "Darwin" else "off"
    if args.smoke and args.job:
        parser.error("Choose either --smoke or --job")
    if args.screenshot and not args.job:
        parser.error("--screenshot requires --job")
    if (args.pointer_test or args.apps_test or args.routing_test or args.update_test or args.welcome_test or args.navigation_test or args.language_test) and not args.screenshot:
        parser.error("Input tests require --screenshot and --job")
    if args.audio == "wav" and not args.audio_file:
        parser.error("--audio wav requires --audio-file")
    if args.audio_file and args.audio != "wav":
        parser.error("--audio-file requires --audio wav")
    if args.display is None:
        args.display = "cocoa" if args.gui else "none"
    if args.gui:
        args.gpu = True
        args.overlay = args.overlay or HERE / "overrides"
        if args.gui == "ccnc" and any(not (args.overlay / "opt/ccnc-qemu" / name).exists()
                                      for name in ("libashmem-qemu.so", "libaudio-platform-qemu.so", "libsettings-platform-qemu.so", "libaudiohal-qemu.so", "libapp-launch-qemu.so", "libmedia-platform-qemu.so")):
            parser.error("Build the compatibility library first: python3 qemu/compat/build.py")
        if args.gui == "ccnc" and not (args.overlay / "opt/ccnc-qemu/mesa/lib/dri/swrast_dri.so").exists():
            parser.error("Prepare CPU OpenGL first: python3 qemu/compat/prepare-mesa.py")
        if args.brand and not (args.overlay / "opt/ccnc-qemu/brand-state.py").is_file():
            parser.error("--brand requires brand-state.py in the selected overlay")
    qemu = shutil.which("qemu-system-aarch64")
    if not qemu:
        parser.error("qemu-system-aarch64 missing; install with: brew install qemu")
    initrd = HERE / "artifacts/ccnc-initramfs.cpio.gz"
    kernel = HERE / "artifacts/alpine/vmlinuz-virt"
    if args.audio != "off" or args.usb_image:
        kernel = HERE / "artifacts/alpine/vmlinuz-lts"
        initrd = HERE / "artifacts/ccnc-audio-initramfs.cpio.gz"
        if not kernel.exists() or not initrd.exists():
            parser.error("Prepare the sound kernel first: python3 qemu/prepare-audio.py")
    image = HERE.parent / "system/1_gos1-fs_7_ext4.img"
    for path in [kernel, initrd, image]:
        if not path.exists():
            parser.error(f"Missing {path}; run python3 qemu/prepare.py first")
    if args.state:
        args.state = args.state.resolve()
        qemu_img = shutil.which("qemu-img")
        if not qemu_img:
            parser.error("qemu-img missing; install with: brew install qemu")
        if args.state.exists():
            info = subprocess.run([qemu_img, "info", "--output=json", str(args.state)],
                                  capture_output=True, text=True)
            if info.returncode:
                parser.error(f"Cannot inspect state disk: {info.stderr.strip()}")
            metadata = json.loads(info.stdout)
            backing = metadata.get("full-backing-filename", "")
            if (metadata.get("format") != "qcow2" or not backing or
                    Path(backing).resolve() != image.resolve() or
                    metadata.get("virtual-size") != image.stat().st_size):
                parser.error("--state must be a qcow2 disk backed by this firmware image")
        elif not args.dry_run:
            args.state.parent.mkdir(parents=True, exist_ok=True)
            # Publish atomically so an existing state disk can never be overwritten.
            with tempfile.TemporaryDirectory(prefix=".ccnc-state-", dir=args.state.parent) as staging:
                disk = Path(staging) / "state.qcow2"
                subprocess.run([qemu_img, "create", "-f", "qcow2", "-F", "raw",
                                "-b", str(image.resolve()), str(disk)], check=True)
                os.link(disk, args.state)
    accel = args.accel
    if accel == "auto":
        accel = "hvf" if platform.system() == "Darwin" and platform.machine() == "arm64" else "tcg"
    # Always use the current init script, including with previously built initramfs files.
    from prepare import cpio_entry
    import gzip
    import stat
    temporary = tempfile.TemporaryDirectory(prefix="ccnc-job-")
    if args.screenshot and not args.qmp:
        args.qmp = Path(temporary.name) / "qmp.sock"
    job_initrd = Path(temporary.name) / "initramfs.gz"
    extra = bytearray()
    extra += cpio_entry("init", (HERE / "guest-init.sh").read_bytes())
    if args.job:
        extra += cpio_entry("ccnc-job.sh", args.job.read_bytes())
    if args.gui:
        extra += cpio_entry("ccnc-gui.sh", (HERE / "graphics-init.sh").read_bytes())
    if args.overlay:
        if not args.overlay.is_dir():
            parser.error("--overlay must be a directory")
        extra += cpio_entry("ccnc-payload", mode=stat.S_IFDIR | 0o755)
        for file in sorted(args.overlay.rglob("*")):
            name = "ccnc-payload/" + file.relative_to(args.overlay).as_posix()
            mode = file.lstat().st_mode
            if file.is_symlink():
                extra += cpio_entry(name, os.readlink(file).encode(), mode)
            elif file.is_dir():
                extra += cpio_entry(name, mode=mode)
            elif file.is_file():
                extra += cpio_entry(name, file.read_bytes(), mode)
    extra += cpio_entry("TRAILER!!!", mode=0)
    job_initrd.write_bytes(initrd.read_bytes() + gzip.compress(extra, mtime=0))
    initrd = job_initrd
    label = {"hyundai": "Hyundai-", "kia": "Kia-"}.get(args.brand, "")
    cmd = [qemu, "-name", label + "ccNC-userspace", "-machine", "virt,gic-version=3",
           "-accel", accel, "-cpu", "host" if accel == "hvf" else "cortex-a57",
           "-smp", str(args.cpus), "-m", str(args.memory), "-display", args.display,
           "-monitor", "none", "-serial", "mon:stdio", "-no-reboot",
           "-nic", "none", "-kernel", str(kernel), "-initrd", str(initrd),
           "-append", "console=ttyAMA0 rdinit=/init loglevel=4 panic=0" +
           (" ccnc.smoke=1" if args.smoke else ""),
           "-blockdev", json.dumps({"driver": "file", "filename": str(image),
                                                 "node-name": "firmware-file", "read-only": True}),
           "-blockdev", "driver=raw,file=firmware-file,node-name=firmware,read-only=on",
           "-device", "virtio-blk-pci,drive=firmware"]
    if args.state:
        cmd[cmd.index("-append") + 1] += " ccnc.state=1"
        cmd += ["-blockdev", json.dumps({"driver": "file", "filename": str(args.state),
                                        "node-name": "state-file"}),
                "-blockdev", "driver=qcow2,file=state-file,backing=firmware,node-name=state",
                "-device", "virtio-blk-pci,drive=state"]
    if args.usb_image:
        cmd[cmd.index("-append") + 1] += " ccnc.usb=1"
        cmd += ["-blockdev", json.dumps({"driver": "file", "filename": str(args.usb_image),
                                       "node-name": "usb-file", "read-only": True}),
                "-blockdev", "driver=raw,file=usb-file,node-name=usb-media,read-only=on",
                "-device", "usb-storage,bus=ccnc-usb.0,drive=usb-media,removable=on,serial=CCNC-LAB-USB"]
    if args.gui:
        cmd[cmd.index("-append") + 1] += f" ccnc.gui={args.gui}"
    if args.brand:
        cmd[cmd.index("-append") + 1] += f" ccnc.brand={args.brand}"
    if args.audio != "off":
        import time
        cmd[cmd.index("-append") + 1] += f" ccnc.audio=1 ccnc.epoch={int(time.time())}"
        backend = {"driver": args.audio, "id": "ccnc-audio"}
        if args.audio == "wav":
            args.audio_file.resolve().parent.mkdir(parents=True, exist_ok=True)
            backend["path"] = str(args.audio_file.resolve())
        cmd += ["-audiodev", json.dumps(backend), "-device", "intel-hda,id=ccnc-hda",
                "-device", "hda-output,bus=ccnc-hda.0,audiodev=ccnc-audio"]
    if args.gpu or args.display != "none" or args.usb_image:
        # Create the controller before any USB devices that reference it.
        cmd[1:1] = ["-device", "qemu-xhci,id=ccnc-usb"]
    if args.gpu or args.display != "none":
        cmd += ["-device", "virtio-gpu-pci,xres=1920,yres=720",
                "-device", "usb-tablet", "-device", "usb-kbd"]
    if args.qmp:
        cmd += ["-qmp", f"unix:{args.qmp.resolve()},server=on,wait=off"]
    if args.dry_run:
        import shlex
        print(shlex.join(cmd))
        return
    if args.smoke or args.job:
        logs = HERE / "logs"
        logs.mkdir(exist_ok=True)
        try:
            if args.screenshot:
                result = run_with_capture(cmd, args.timeout, args.screenshot, args.qmp, args.pointer_test, args.apps_test, args.routing_test, args.audio_file, args.update_test, args.welcome_test, args.navigation_test, args.language_test)
            else:
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=args.timeout)
        except subprocess.TimeoutExpired as error:
            finalize_wav(args.audio_file)
            output = error.stdout or b""
            (logs / ("job.log" if args.job else "smoke.log")).write_bytes(output)
            print(output.decode(errors="replace"))
            raise SystemExit("VM job timed out; see qemu/logs")
        finalize_wav(args.audio_file)
        if args.job:
            (logs / "job.log").write_bytes(result.stdout)
            (logs / f"{args.job.stem}.log").write_bytes(result.stdout)
            print(result.stdout.decode(errors="replace"))
            if result.returncode or b"CCNC_JOB_EXIT=0" not in result.stdout:
                raise SystemExit("VM job failed; see qemu/logs/job.log")
            return
        (logs / "smoke.log").write_bytes(result.stdout)
        (logs / f"smoke-{accel}.log").write_bytes(result.stdout)
        print(result.stdout.decode(errors="replace"))
        if result.returncode or b"CCNC_USERSPACE_OK" not in result.stdout or b"CCNC_SMOKE_EXIT=0" not in result.stdout:
            raise SystemExit("Smoke test failed; see qemu/logs/smoke.log")
        print("PASS: original ccNC ARM64 userspace executed inside QEMU.")
    else:
        status = subprocess.call(cmd)
        finalize_wav(args.audio_file)
        raise SystemExit(status)


if __name__ == "__main__":
    main()
